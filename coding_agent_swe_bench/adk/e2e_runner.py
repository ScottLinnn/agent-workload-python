import asyncio
import os
import sys

# Add current dir to path to import agent modules
current_dir = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(current_dir)) # Two levels up from adk/ is the parent of coding_agent
sys.path.append(REPO_ROOT)

from coding_agent_swe_bench.adk.run_agent import run_agent_flow
from coding_agent_swe_bench.adk.evaluator import evaluate

async def run_e2e():
    print("=== Phase 1: Running Coding Agent ===")
    try:
        await run_agent_flow()
    except Exception as e:
        print(f"Agent execution failed: {e}")
        return False
        
    print("\n=== Phase 2: Evaluating Results ===")
    if await evaluate():
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
