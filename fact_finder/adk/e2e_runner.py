import asyncio
import os
import sys

# Add current dir to path to import agent modules
# Absolute path to the root of agent_tasks
# Absolute path to the root of the repo (relative to this file)
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(ROOT_PATH)

from fact_finder.adk.run_agent import main as run_agent
from fact_finder.adk.evaluator import evaluate

async def run_e2e():
    print("=== Phase 1: Running Fact Finder Agent ===")
    try:
        await run_agent()
    except Exception as e:
        print(f"Agent execution failed: {e}")
        return False
        
    print("\n=== Phase 2: Evaluating Results ===")
    # Evaluator reads from standardized path
    result_path = os.path.join(os.path.dirname(__file__), 'fact_finder_result.txt')
    if not os.path.exists(result_path):
        print(f"FAILED: {result_path} not found.")
        return False
        
    with open(result_path, 'r') as f:
        response_text = f.read()
        
    if evaluate(response_text):
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
