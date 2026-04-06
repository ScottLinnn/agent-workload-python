import asyncio
import json
import os
import subprocess
import sys
from absl import app
from absl import flags

FLAGS = flags.FLAGS


def get_git_env() -> dict[str, str]:
  """Set up Git environment with deploy key if available."""
  env = os.environ.copy()
  deploy_key = os.environ.get("GITHUB_DEPLOY_KEY")
  if deploy_key:
    print("Using GITHUB_DEPLOY_KEY for git operations.")
    key_file = "/tmp/eval_deploy_key"
    with open(key_file, "w") as f:
      f.write(deploy_key)
    os.chmod(key_file, 0o600)
    env["GIT_SSH_COMMAND"] = f"ssh -i {key_file} -o StrictHostKeyChecking=no"
  return env


def prepare_repo_remote(
    repo_dir: str, repo: str, branch: str | None, env: dict[str, str]
) -> bool:
  """Pull repo and checkout result branch for remote evaluation."""
  clone_url = f"git@github.com:{repo}.git"

  if not os.path.exists(repo_dir):
    print(
        f"Repository directory {repo_dir} not found. Cloning from"
        f" {clone_url}..."
    )
    res = subprocess.run(
        ["git", "clone", clone_url, repo_dir],
        capture_output=True,
        text=True,
        env=env,
    )
    if res.returncode != 0:
      print(f"FAILED to clone repo: {res.stderr}")
      return False

  # Read branch name if not provided
  if not branch:
    if os.path.exists("agent_result_branch.txt"):
      with open("agent_result_branch.txt", "r") as f:
        branch = f.read().strip()
    else:
      branch = os.environ.get("AGENT_BRANCH")

  if not branch:
    print("FAILED: No result branch found for remote evaluation.")
    return False

  print(f"Found branch to evaluate: {branch}")
  print("Fetching and checking out branch...")
  res = subprocess.run(
      ["git", "fetch", "origin"],
      cwd=repo_dir,
      capture_output=True,
      text=True,
      env=env,
  )
  if res.returncode != 0:
    print(f"Warning: Failed to fetch: {res.stderr}")

  res = subprocess.run(
      ["git", "checkout", branch],
      cwd=repo_dir,
      capture_output=True,
      text=True,
      env=env,
  )
  if res.returncode != 0:
    print(f"FAILED to checkout branch {branch}: {res.stderr}")
    return False

  return True


def prepare_repo_local(repo_dir: str) -> bool:
  """Verify local repo exists for local evaluation."""
  if not os.path.exists(repo_dir):
    print(
        f"FAILED: Local search repository directory {repo_dir} not found. Local"
        " eval expects it to be present."
    )
    return False
  return True


def setup_environment(repo_dir: str) -> bool:
  """Create venv and install dependencies in workspace_repo."""
  print("Setting up environment in workspace_repo...")
  res = subprocess.run(
      [sys.executable, "-m", "venv", "venv"],
      cwd=repo_dir,
      capture_output=True,
      text=True,
  )
  if res.returncode != 0:
    print(f"FAILED to create venv: {res.stderr}")
    return False

  pip_path = os.path.join(repo_dir, "venv", "bin", "pip")

  requirements_path = os.path.join(repo_dir, "requirements.txt")
  setup_py_path = os.path.join(repo_dir, "setup.py")
  pyproject_toml_path = os.path.join(repo_dir, "pyproject.toml")

  if os.path.exists(requirements_path):
    print("Installing from requirements.txt...")
    res = subprocess.run(
        [
            pip_path,
            "install",
            "--index-url",
            "https://pypi.org/simple",
            "-r",
            "requirements.txt",
        ],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
  elif os.path.exists(setup_py_path) or os.path.exists(pyproject_toml_path):
    print("Installing editable...")
    res = subprocess.run(
        [
            pip_path,
            "install",
            "--index-url",
            "https://pypi.org/simple",
            "-e",
            ".",
        ],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
  else:
    print(
        "No standard dependency file found. Skipping dependency installation."
    )
    return True

  if res.returncode != 0:
    print(f"Warning: Dependency installation failed: {res.stderr}")

  return True


def apply_test_patch(repo_dir: str, test_patch: str) -> bool:
  """Apply test patch to the repository."""
  print("Applying test patch...")
  patch_path = os.path.join(repo_dir, "test_patch.diff")
  with open(patch_path, "w") as f:
    f.write(test_patch)

  res = subprocess.run(
      ["git", "apply", "test_patch.diff"],
      cwd=repo_dir,
      capture_output=True,
      text=True,
  )
  if res.returncode != 0:
    print(f"Warning: Failed to apply test patch: {res.stderr}")
    return False
  return True


def run_tests(repo_dir: str, tests: list[str], pytest_path: str) -> bool:
  """Run specified tests using pytest."""
  all_passed = True
  for test in tests:
    print(f"Running {test}...")
    res = subprocess.run(
        [pytest_path, test], cwd=repo_dir, capture_output=True, text=True
    )
    if res.returncode != 0:
      print(f"FAILED: {test}\n{res.stdout}\n{res.stderr}")
      all_passed = False
    else:
      print(f"PASSED: {test}")
  return all_passed


async def evaluate() -> bool:
  """Evaluate the agent execution."""
  try:
    remote = FLAGS.remote
  except AttributeError:
    remote = False

  branch = None
  if os.path.exists("agent_result_branch.txt"):
    with open("agent_result_branch.txt", "r") as f:
      branch = f.read().strip()

  if remote and not branch:
    print(
        "Error: Remote evaluation requires agent_result_branch.txt to be"
        " present."
    )
    return False

  datum_path = os.environ.get("SWEBENCH_DATUM_PATH", "swebench_datum.json")
  if not os.path.exists(datum_path):
    # Try looking in specific directory if found in ls -R earlier
    alt_datum_path = "coding_agent_swe_bench/swebench_datum.json"
    if os.path.exists(alt_datum_path):
      datum_path = alt_datum_path
    else:
      print(f"FAILED: SWE-bench datum file not found at {datum_path}")
      return False

  with open(datum_path, "r") as f:
    datum = json.load(f)

  evaluator_dir = os.path.dirname(os.path.abspath(__file__))
  repo_root = os.path.dirname(os.path.dirname(evaluator_dir))
  repo_dir = os.path.join(repo_root, "workspace_repo")
  repo = datum.get("repo")

  env = get_git_env()

  if remote:
    if not prepare_repo_remote(repo_dir, repo, branch, env):
      return False
    if not setup_environment(repo_dir):
      return False
  else:
    if not prepare_repo_local(repo_dir):
      return False

  test_patch = datum.get("test_patch")
  if test_patch:
    apply_test_patch(repo_dir, test_patch)

  venv_pytest = os.path.join(repo_dir, "venv", "bin", "pytest")
  if os.path.exists(venv_pytest):
    pytest_path = venv_pytest
    print(f"Using pytest from workspace venv: {pytest_path}")
  else:
    pytest_path = os.path.join(os.path.dirname(sys.executable), "pytest")
    print(f"Using system/runner pytest: {pytest_path}")

  fail_to_pass = datum.get("FAIL_TO_PASS", [])
  if isinstance(fail_to_pass, str):
    try:
      fail_to_pass = json.loads(fail_to_pass)
    except:
      fail_to_pass = [fail_to_pass]

  print(f"\nRunning FAIL_TO_PASS tests: {fail_to_pass}")
  all_passed = run_tests(repo_dir, fail_to_pass, pytest_path)

  pass_to_pass = datum.get("PASS_TO_PASS", [])
  if isinstance(pass_to_pass, str):
    try:
      pass_to_pass = json.loads(pass_to_pass)
    except:
      pass_to_pass = [pass_to_pass]

  print(f"\nRunning PASS_TO_PASS tests: {pass_to_pass}")
  all_passed = run_tests(repo_dir, pass_to_pass, pytest_path) and all_passed

  if all_passed:
    print("\nSUCCESS: SWE-bench evaluation passed!")
    return True
  else:
    print("\nFAILURE: SWE-bench evaluation failed.")
    return False


def main(argv):
  if asyncio.run(evaluate()):
    sys.exit(0)
  else:
    sys.exit(1)


if __name__ == "__main__":
  app.run(main)
