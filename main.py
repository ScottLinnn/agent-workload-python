import asyncio
import sys
import os
import importlib
from dotenv import load_dotenv
from absl import flags
from absl import app

FLAGS = flags.FLAGS

flags.DEFINE_string('task', None, 'Task to work on')
flags.DEFINE_string('framework', None, 'Framework to use')
flags.DEFINE_boolean('remote', False, 'Run remotely using Vertex AI Agent Engine')
flags.DEFINE_string('agent_engine_id', None, 'Agent Engine resource ID')

# Load environment variables from .env file
load_dotenv()

# Root of the repo
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(REPO_ROOT)

def run_task(task, framework):
    print(f"=== Running Task: {task} | Framework: {framework} ===")
    
    # Loaded from .env or environment
    os.environ.setdefault('GOOGLE_GENAI_USE_VERTEXAI', '1')
    if not os.environ.get('GOOGLE_CLOUD_LOCATION'):
        print("Error: GOOGLE_CLOUD_LOCATION must be set in environment or .env file.")
        sys.exit(1)
    if not os.environ.get('GOOGLE_CLOUD_PROJECT'):
        print("Error: GOOGLE_CLOUD_PROJECT must be set in environment or .env file.")
        sys.exit(1)

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

def main(argv):
    if not FLAGS.task:
        print("Error: --task flag is required.")
        sys.exit(1)
    if not FLAGS.framework:
        print("Error: --framework flag is required.")
        sys.exit(1)

    # Validation for remote
    if FLAGS.remote:
        valid = True
        if FLAGS.framework not in ["adk", "langgraph"]:
             print("Validation Error: Remote execution requires framework to be 'adk' or 'langgraph'.")
             valid = False
        if FLAGS.task not in ["coding_agent_swe_bench", "data_science"]:
             print("Validation Error: Remote execution requires task to be 'coding_agent_swe_bench' or 'data_science'.")
             valid = False
        if not FLAGS.agent_engine_id:
             print("Validation Error: Remote execution requires agent_engine_id to be supplied.")
             valid = False
             
        if not valid:
             print("Notice: More frameworks and more tasks will be supported in the future.")
             sys.exit(1)

    if run_task(FLAGS.task, FLAGS.framework):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    app.run(main)
