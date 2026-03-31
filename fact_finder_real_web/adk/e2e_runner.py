import asyncio
import os
import sys

from fact_finder_real_web.adk.evaluator import evaluate
from fact_finder_real_web.adk.run_agent import main as run_agent

async def run_e2e():
    print("=== Phase 1: Running Fact Finder Real Web Agent ===")
    try:
        # Note: This will perform real web search and scraping
        await run_agent()
    except Exception as e:
        print(f"Agent execution failed: {e}")
        return False
        
    print("\n=== Phase 2: Evaluating Results ===")
    # Evaluator reads from standardized path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    result_path = os.path.join(current_dir, 'fact_finder_result.txt')
    
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
