import sys
import os
import asyncio
import json
import subprocess

async def evaluate():
    datum_path = os.environ.get('SWEBENCH_DATUM_PATH', 'swe_bench_datum.json')
    if not os.path.exists(datum_path):
        print(f"FAILED: SWE-bench datum file not found at {datum_path}")
        return False
        
    with open(datum_path, 'r') as f:
        datum = json.load(f)
        
    repo_dir = 'workspace_repo'
    repo = datum.get('repo')
    clone_url = f"git@github.com:{repo}.git"

    # Setup git environment if key is available
    deploy_key = os.environ.get("GITHUB_DEPLOY_KEY")
    git_ssh_cmd = None
    env = os.environ.copy()
    if deploy_key:
        print("Using GITHUB_DEPLOY_KEY for git operations.")
        key_file = "/tmp/eval_deploy_key"
        with open(key_file, "w") as f:
            f.write(deploy_key)
        os.chmod(key_file, 0o600)
        git_ssh_cmd = f'ssh -i {key_file} -o StrictHostKeyChecking=no'
        env["GIT_SSH_COMMAND"] = git_ssh_cmd

    if not os.path.exists(repo_dir):
        print(f"Repository directory {repo_dir} not found. Cloning from {clone_url}...")
        res = subprocess.run(["git", "clone", clone_url, repo_dir], capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"FAILED to clone repo: {res.stderr}")
            return False
            
    # Read branch name
    branch = None
    if os.path.exists("agent_result_branch.txt"):
        with open("agent_result_branch.txt", "r") as f:
            branch = f.read().strip()
            
    if not branch:
        branch = os.environ.get("AGENT_BRANCH")
        
    if branch:
        print(f"Found branch to evaluate: {branch}")
        print("Fetching and checking out branch...")
        res = subprocess.run(["git", "fetch", "origin"], cwd=repo_dir, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"Warning: Failed to fetch: {res.stderr}")
            
        res = subprocess.run(["git", "checkout", branch], cwd=repo_dir, capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"FAILED to checkout branch {branch}: {res.stderr}")
            return False
    else:
        print("No branch specified or found in agent_result_branch.txt. Proceeding with current state.")
        
    test_patch = datum.get('test_patch')
    if test_patch:
        print("Applying test patch...")
        patch_path = os.path.join(repo_dir, 'test_patch.diff')
        with open(patch_path, 'w') as f:
            f.write(test_patch)
            
        # Try applying patch
        res = subprocess.run(["git", "apply", "test_patch.diff"], cwd=repo_dir, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Warning: Failed to apply test patch: {res.stderr}")
            # Might continue anyway if tests are already there or patch is partial
            
    # Run FAIL_TO_PASS tests
    fail_to_pass = datum.get('FAIL_TO_PASS', [])
    if isinstance(fail_to_pass, str):
        try:
            fail_to_pass = json.loads(fail_to_pass)
        except:
            fail_to_pass = [fail_to_pass]
            
    pytest_path = os.path.join(os.path.dirname(sys.executable), "pytest")
        
    all_passed = True
    print(f"\nRunning FAIL_TO_PASS tests: {fail_to_pass}")
    for test in fail_to_pass:
        print(f"Running {test}...")
        # This is a simplified run, assuming test string works with pytest
        res = subprocess.run([pytest_path, test], cwd=repo_dir, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FAILED: {test}\n{res.stdout}\n{res.stderr}")
            all_passed = False
        else:
            print(f"PASSED: {test}")
            
    # We could also run PASS_TO_PASS but for simplicity let's focus on FAIL_TO_PASS first
    # or just run them if present
    pass_to_pass = datum.get('PASS_TO_PASS', [])
    if isinstance(pass_to_pass, str):
        try:
            pass_to_pass = json.loads(pass_to_pass)
        except:
            pass_to_pass = [pass_to_pass]
            
    print(f"\nRunning PASS_TO_PASS tests: {pass_to_pass}")
    for test in pass_to_pass:
        print(f"Running {test}...")
        res = subprocess.run([pytest_path, test], cwd=repo_dir, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FAILED (Regression): {test}\n{res.stdout}\n{res.stderr}")
            all_passed = False
        else:
            print(f"PASSED: {test}")

    if all_passed:
        print("\nSUCCESS: SWE-bench evaluation passed!")
        return True
    else:
        print("\nFAILURE: SWE-bench evaluation failed.")
        return False

if __name__ == "__main__":
    if asyncio.run(evaluate()):
        sys.exit(0)
    else:
        sys.exit(1)
