import asyncio
from datetime import datetime
import json
import os
import re
import subprocess
import sys
from absl import app
from absl import flags
from dotenv import load_dotenv

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
from coding_agent_swe_bench.langgraph.agent import coding_agent_langgraph
import vertexai
import traceback


async def run():
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
   - The framework name: "langgraph"
   - What issue it's fixing (e.g., a short keyword describing the fix).
   - A random number.
   - Example: `langgraph-fix-missing-colon-4827`
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
        # Local execution using the LanggraphAgent wrapper
        print("Running LangGraph agent locally...")
        # stream_query is a generator
        for chunk in coding_agent_langgraph.stream_query(
            input={
                "messages": [{"role": "user", "content": setup_instructions}]
            },
            config={"recursion_limit": 100},
        ):
          print(chunk)
          # We might want to parse RESULT_BRANCH here too if needed for local test
          # But usually local test is just for debugging.

      else:
        # Remote execution via Vertex AI SDK
        print(f"Querying remote LangGraph agent (ID: {agent_engine_id})...")
        client = vertexai.Client(project=project_id, location=location)
        langgraph_app = client.agent_engines.get(
            name=f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
        )

        result_branch = None
        for chunk in langgraph_app.stream_query(
            input={
                "messages": [{"role": "user", "content": setup_instructions}]
            },
            config={"recursion_limit": 100},
        ):
          print(chunk)
          # Parse RESULT_BRANCH
          if isinstance(chunk, dict):
            for node_name, node_output in chunk.items():
              if isinstance(node_output, dict) and "messages" in node_output:
                for msg in node_output["messages"]:
                  content = ""
                  if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if not content and "kwargs" in msg:
                      content = msg["kwargs"].get("content", "")
                  elif hasattr(msg, "content"):
                    content = msg.content

                  if isinstance(content, list):
                    for part in content:
                      if isinstance(part, dict) and "text" in part:
                        text = part["text"]
                        matches = re.findall(
                            r"RESULT_BRANCH:\s*([\w\-]+)", text
                        )
                        if matches:
                          result_branch = matches[-1]
                  elif isinstance(content, str):
                    matches = re.findall(r"RESULT_BRANCH:\s*([\w\-]+)", content)
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

def main(argv):
    asyncio.run(run())

if __name__ == "__main__":
    app.run(main)
