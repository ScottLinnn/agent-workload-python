import asyncio
import os
import sys
import shutil

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from data_science.mock_data_gen import generate_mock_data
from data_science.adk.run_agent import main as run_agent
from data_science.adk.evaluator import evaluate

async def run_e2e():
    print("=== Phase 0: Cleaning up old results ===")
    results_dir = os.path.join(os.getcwd(), "adk_data_science_results")
    if os.path.exists(results_dir):
        print(f"Deleting old results directory: {results_dir}")
        shutil.rmtree(results_dir)
        
    print("\n=== Phase 1: Generating Mock Data ===")
    generate_mock_data()
    
    print("\n=== Phase 2: Running Data Science Agent ===")
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
