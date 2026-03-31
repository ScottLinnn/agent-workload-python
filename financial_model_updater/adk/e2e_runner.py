import asyncio
import os
import sys

# Add current dir to path to import agent modules
# Absolute path to the root of the repo (relative to this file)
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(ROOT_PATH)

from financial_model_updater.adk.mock_data_gen import generate_mock_data
from financial_model_updater.adk.run_agent import main as run_agent
from financial_model_updater.adk.evaluator import evaluate

async def run_e2e():
    print("=== Phase 1: Generating Mock Data ===")
    generate_mock_data()
    
    print("\n=== Phase 2: Running Financial Agent ===")
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
