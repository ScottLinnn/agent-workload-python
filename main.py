import argparse
import asyncio
import sys
import os
import importlib
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Root of the repo
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(REPO_ROOT)

def run_task(task, framework):
    print(f"=== Running Task: {task} | Framework: {framework} ===")
    
    # Loaded from .env or environment
    os.environ.setdefault('GOOGLE_GENAI_USE_VERTEXAI', '1')
    os.environ.setdefault('GOOGLE_CLOUD_LOCATION', os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1'))
    os.environ.setdefault('GOOGLE_CLOUD_PROJECT', os.getenv('GOOGLE_CLOUD_PROJECT'))

    if framework == "adk":
        # Import e2e_runner from adk folder
        # We need to use absolute import from the root because we added REPO_ROOT to sys.path
        module_path = f"{task}.adk.e2e_runner"
        try:
            e2e_module = importlib.import_module(module_path)
            if hasattr(e2e_module, 'run_e2e'):
                result = asyncio.run(e2e_module.run_e2e())
                return result
            else:
                print(f"Error: run_e2e not found in {module_path}")
                return False
        except ImportError as e:
            print(f"Error: Failed to import {module_path}: {e}")
            return False
            
    elif framework == "langgraph":
        # Check if langgraph version exists
        langgraph_path = os.path.join(REPO_ROOT, task, "langgraph")
        if not os.path.exists(langgraph_path):
            print(f"Error: LangGraph version of {task} does not exist.")
            return False
            
        # For LangGraph, we run run_agent and then evaluation from adk
        run_agent_module_path = f"{task}.langgraph.run_agent"
        eval_module_path = f"{task}.adk.evaluator"
        
        try:
            print(f"--- Phase 1: Running {task} (LangGraph) ---")
            run_module = importlib.import_module(run_agent_module_path)
            # Some uses 'main(argv)', some uses 'run()'
            if hasattr(run_module, 'run'):
                asyncio.run(run_module.run())
            elif hasattr(run_module, 'main'):
                 asyncio.run(run_module.main([])) # main expects argv
            else:
                print(f"Error: run or main not found in {run_agent_module_path}")
                return False
                
            print(f"\n--- Phase 2: Evaluating Results for {task} ---")
            eval_module = importlib.import_module(eval_module_path)
            if hasattr(eval_module, 'evaluate'):
                if asyncio.iscoroutinefunction(eval_module.evaluate):
                    result = asyncio.run(eval_module.evaluate())
                else:
                    result = eval_module.evaluate()
                    
                if result:
                    print("\nSUCCESS: End-to-end verification passed!")
                    return True
                else:
                    print("\nFAILURE: Evaluation failed.")
                    return False
            else:
                print(f"Error: evaluate not found in {eval_module_path}")
                return False
        except ImportError as e:
            print(f"Error: Missing module for {task}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Run agentic-workload-python tasks")
    parser.add_argument("--task", type=str, required=True, 
                        choices=["bug_triage", "fact_finder", "fact_finder_real_web", "financial_model_updater", "itinerary_planner", "coding_agent_pkb", "coding_agent_swe_bench", "data_science"], 
                        help="Task to work on")
    parser.add_argument("--framework", type=str, required=True, 
                        choices=["adk", "langgraph"], 
                        help="Framework to use")
    parser.add_argument("--remote", action="store_true", help="Run remotely using Vertex AI Agent Engine")
    parser.add_argument("--agent_engine_id", type=str, default="6153237054697242624", help="Agent Engine resource ID")
    
    args, _ = parser.parse_known_args()
    if run_task(args.task, args.framework):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
