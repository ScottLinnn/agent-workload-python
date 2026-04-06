import asyncio
from datetime import datetime
import json
import os
import re
import subprocess
import sys
from dotenv import load_dotenv
from absl import flags

FLAGS = flags.FLAGS

load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
if not os.environ.get("GOOGLE_CLOUD_LOCATION"):
  print("Error: GOOGLE_CLOUD_LOCATION must be set in environment or .env file.")
  sys.exit(1)
if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
  print("Error: GOOGLE_CLOUD_PROJECT must be set in environment or .env file.")
  sys.exit(1)
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)
from coding_agent_swe_bench.adk.agent import coding_agent
from google.adk.events.event import Event
from google.adk.utils._debug_output import print_event
from google.genai import types
import vertexai
import traceback


def setup_environment(datum: dict):
  repo = datum.get("repo")
  base_commit = datum.get("base_commit")
  env_setup_commit = datum.get("environment_setup_commit", base_commit)

  print(f"Setting up environment for {repo}...")

  # Construct clone URL assuming github for now, but could be adjusted
  clone_url = f"https://github.com/{repo}.git"

  # Clone into 'workspace_repo'
  if os.path.exists("workspace_repo"):
    print("workspace_repo already exists, removing...")
    subprocess.run(["rm", "-rf", "workspace_repo"])

  subprocess.run(["git", "clone", clone_url, "workspace_repo"], check=True)

  # 1. Checkout environment_setup_commit
  print(f"Checking out environment setup commit {env_setup_commit}...")
  subprocess.run(
      ["git", "checkout", env_setup_commit], cwd="workspace_repo", check=True
  )

  # 2. Init venv and create dependencies
  print("Setting up venv...")
  subprocess.run(
      [sys.executable, "-m", "venv", "venv"], cwd="workspace_repo", check=True
  )
  pip_path = os.path.join("venv", "bin", "pip")

  # Attempt to install dependencies using pip
  print("Installing dependencies...")
  # Try standard editable install which works for most modern python repos
  # Or look for requirements.txt
  if os.path.exists(os.path.join("workspace_repo", "requirements.txt")):
    subprocess.run(
        [pip_path, "install", "--index-url", "https://pypi.org/simple", "-r", "requirements.txt"],
        cwd="workspace_repo",
        check=False,
    )
  else:
    subprocess.run(
        [pip_path, "install", "--index-url", "https://pypi.org/simple", "-e", "."], cwd="workspace_repo", check=False
    )

  # 3. Checkout base_commit for the agent run
  print(f"Checking out base commit {base_commit} for agent run...")
  subprocess.run(
      ["git", "checkout", base_commit], cwd="workspace_repo", check=True
  )


async def run_agent_flow():
  try:
    remote = FLAGS.remote
    agent_engine_id = FLAGS.agent_engine_id
  except AttributeError as e:
    print(f"Error: Flags not initialized properly: {e}")
    sys.exit(1)

  if remote and not agent_engine_id:
    print("Error: --agent_engine_id must be provided for remote runs.")
    sys.exit(1)

  # Cleanup old files
  for f in ["agent_tool_log.txt", "agent_result_branch.txt"]:
    if os.path.exists(f):
      os.remove(f)

  datum_path = os.environ.get(
      "SWEBENCH_DATUM_PATH", "swebench_test_repo_v5.json"
  )
  if not os.path.exists(datum_path):
    # Try looking in specific directory
    alt_datum_path = "coding_agent_swe_bench/swebench_test_repo_v5.json"
    if os.path.exists(alt_datum_path):
      datum_path = alt_datum_path
    else:
      print(f"Error: SWE-bench datum file not found at {datum_path}")
      return

  with open(datum_path, "r") as f:
    datum = json.load(f)

  repo = datum.get("repo")
  base_commit = datum.get("base_commit")
  env_setup_commit = datum.get("environment_setup_commit", base_commit)
  problem_statement = datum.get(
      "problem_statement", "No problem statement provided."
  )

  setup_instructions = f"""
Before solving the issue, you MUST set up the environment by performing the following steps in order:
1. Read the `GITHUB_DEPLOY_KEY` environment variable.
2. Write the content of `GITHUB_DEPLOY_KEY` to a file, for example `/tmp/deploy_key`.
3. Set the permissions of the key file to be read-only by the owner (e.g., `chmod 600 /tmp/deploy_key`).
4. Configure git dummy user name and email:
   - `git config --global user.name "Agent"`
   - `git config --global user.email "agent@google.com"`
5. Clone the repository `git@github.com:{repo}.git` into a directory named `workspace_repo` using the deploy key.
   - You can use `GIT_SSH_COMMAND="ssh -i /tmp/deploy_key -o StrictHostKeyChecking=no"` for git operations.
   - Example: `GIT_SSH_COMMAND="ssh -i /tmp/deploy_key -o StrictHostKeyChecking=no" git clone git@github.com:{repo}.git workspace_repo`
6. Check out the environment setup commit `{env_setup_commit}`.
   - Use `run_shell_command` with `cwd='workspace_repo'`.
7. Set up a virtual environment named `venv` inside `workspace_repo` and install dependencies.
8. Check out the base commit `{base_commit}` for the actual agent run.

After you have solved the issue and made a commit:
1. Create a dynamic branch name that includes:
   - The framework name: "adk"
   - What issue it's fixing (e.g., a short keyword describing the fix).
   - A random number.
   - Example: `adk-fix-missing-colon-4827`
   - If the branch name already exists on remote, reinvent a new random number and try again.
   You can simply invent a random number in your head (e.g., 4827) and use it. You do not need to use a tool or python to generate it.
2. Checkout that branch.
3. Push the branch to remote origin using the deploy key.
   - Example: `GIT_SSH_COMMAND="ssh -i /tmp/deploy_key -o StrictHostKeyChecking=no" git push origin <branch_name>`
4. **Crucial**: Print `RESULT_BRANCH: <branch_name>` in your final response so the evaluator knows which branch to test.

Solve the following issue:

{problem_statement}
"""

  project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
  location = os.environ["GOOGLE_CLOUD_LOCATION"]

  try:
    with open("agent_tool_log.txt", "a") as log_file:
      log_file.write(f"--- Starting Agent Run ---\n")
      log_file.write(f"Current time: {datetime.now()}\n")

      if not remote:
        # Local execution
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService

        runner = Runner(
            app_name="coding_agent_swe_bench",
            agent=coding_agent,
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        async for event in runner.run_async(
            user_id="shuninglin",
            session_id="session-1",
            new_message=types.Content(
                parts=[types.Part(text=setup_instructions)]
            ),
        ):
          print_event(event)
          if event.content and event.content.parts:
            for part in event.content.parts:
              if part.function_call:
                log_file.write(
                    f"--- Tool Call: {part.function_call.name} ---\n"
                )
                log_file.write(f"Args: {part.function_call.args}\n\n")
              elif part.function_response:
                log_file.write(f"--- Tool Output ---\n")
                log_file.write(f"Result: {part.function_response.response}\n\n")

      else:
        # Remote execution via Vertex AI SDK directly
        client = vertexai.Client(project=project_id, location=location)
        adk_app = client.agent_engines.get(
            name=f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
        )

        result_branch = None
        async for event in adk_app.async_stream_query(
            user_id="shuninglin",
            message=setup_instructions,
        ):
          if isinstance(event, dict):
            event = Event.model_validate(event)
          if event.content and event.content.parts:
            for part in event.content.parts:
              if part.text:
                print(part.text)
                matches = re.findall(r"RESULT_BRANCH:\s*([\w\-]+)", part.text)
                if matches:
                  result_branch = matches[-1]
              elif part.function_call:
                print(f"[Function Call]: {part.function_call.name}")
                log_file.write(
                    f"--- Tool Call: {part.function_call.name} ---\n"
                )
                log_file.write(f"Args: {part.function_call.args}\n\n")
              elif part.function_response:
                log_file.write(f"--- Tool Output ---\n")
                log_file.write(f"Result: {part.function_response.response}\n\n")
                response_str = str(part.function_response.response)
                matches = re.findall(
                    r"RESULT_BRANCH:\s*([\w\-]+)", response_str
                )
                if matches:
                  result_branch = matches[-1]

        if result_branch:
          print(f"\n[Success] Found result branch: {result_branch}")
          with open("agent_result_branch.txt", "w") as f:
            f.write(result_branch)
        else:
          print("\n[Warning] No RESULT_BRANCH found in agent output.")

  except Exception as e:
    print(f"Agent execution crashed:")
    traceback.print_exc()
    raise e
