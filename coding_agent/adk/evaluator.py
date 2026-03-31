import sys
import os
import asyncio

async def evaluate():
    workspace_base = os.environ.get("WORKSPACE_BASE", os.getcwd())
    resolved_issue_path = os.path.join(workspace_base, 'resolved_issue.md')
    execution_history_path = os.path.join(workspace_base, 'execution_history.md')
    
    if not os.path.exists(resolved_issue_path):
        print(f"FAILED: {resolved_issue_path} does not exist.")
        return False
        
    if not os.path.exists(execution_history_path):
        print(f"FAILED: {execution_history_path} does not exist.")
        return False
        
    with open(resolved_issue_path, 'r') as f:
        resolved_content = f.read().strip()
        
    if not resolved_content:
        print("FAILED: resolved_issue.md is empty.")
        return False
        
    print(f"SUCCESS: Found resolved_issue.md with content:\n{resolved_content}")
    return True

if __name__ == "__main__":
    if asyncio.run(evaluate()):
        sys.exit(0)
    else:
        sys.exit(1)
