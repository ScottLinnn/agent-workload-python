import asyncio
import os
import shutil
import sys
from absl import flags

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
  sys.path.append(ROOT_PATH)

from agentic_rag.mock_data_gen import generate_mock_data
from agentic_rag.adk.run_agent import main as run_agent
from agentic_rag.adk.evaluator import evaluate

FLAGS = flags.FLAGS
try:
  flags.DEFINE_boolean("remote", False, "Run agent remotely on Vertex AI")
except flags.DuplicateFlagError:
  pass


async def run_e2e():
  print("=== Phase 0: Cleaning up old results ===")
  results_dir = os.path.join(os.getcwd(), "adk_rag_agent_results")
  if os.path.exists(results_dir):
    print(f"Deleting old results directory: {results_dir}")
    shutil.rmtree(results_dir)

  try:
    FLAGS(sys.argv)
  except flags.UnparsedFlagAccessError:
    pass

  if not FLAGS.remote:
    print("\n=== Phase 1: Generating Mock Data ===")
    generate_mock_data()
  else:
    print("\n=== Phase 1: Skipping Mock Data Generation (Remote Mode) ===")

  print("\n=== Phase 2: Running RAG Agent ===")
  try:
    await run_agent()
  except Exception as e:
    print(f"Agent execution failed: {e}")
    return False

  print("\n=== Phase 3: Evaluating Results ===")
  if evaluate():
    print("\nSUCCESS: End-to-end verification passed!")
    return True
  else:
    print("\nFAILURE: Evaluation failed.")
    return False


if __name__ == "__main__":
  if asyncio.run(run_e2e()):
    sys.exit(0)
  else:
    sys.exit(1)
