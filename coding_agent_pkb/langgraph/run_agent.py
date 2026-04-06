import os
import sys
import asyncio

from google.cloud import aiplatform
from absl import app

from coding_agent.langgraph.agent import coding_agent_langgraph, WORKSPACE_FILES, GIT_LOG

async def run():
    try:
        aiplatform.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        config = {"configurable": {"thread_id": "session_langgraph_1"}, "recursion_limit": 100}
        inputs = {"messages": [("user", "Go to the PerfKitBenchmarker issues page, pick an issue, and attempt to resolve it in our local clone in the current directory.")]}

        print("Starting LangGraph runner...")
        async for chunk in coding_agent_langgraph.astream(inputs, config=config, stream_mode="updates"):
            for node, values in chunk.items():
                print(f"\n--- Node: {node} ---")
                if "messages" in values:
                    for msg in values["messages"]:
                        msg.pretty_print()

        print(f"\nFinal State of Workspace:")
        for path, content in WORKSPACE_FILES.items():
            print(f"--- {path} ---")
            print(content)
        
        print(f"\nGit Commits: {GIT_LOG}")
    except Exception as e:
        print(f"Exception in run: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main(argv):
    asyncio.run(run())

if __name__ == "__main__":
    app.run(main)
