import os
import sys
import asyncio
from absl import app
from google.cloud import aiplatform as vertexai

from financial_model_updater.langgraph.agent import financial_langgraph_agent

async def run():
    try:
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        config = {"configurable": {"thread_id": "session_langgraph_3"}}
        inputs = {"messages": [("user", "Process the Q4 revenue estimates from q4_data.txt, update the model.xlsx, recalculate IRR, and save the summary to summary.md.")]}

        print("Starting LangGraph runner...")
        async for chunk in financial_langgraph_agent.astream(inputs, config=config, stream_mode="updates"):
            for node, values in chunk.items():
                print(f"\n--- Node: {node} ---")
                if "messages" in values:
                    for msg in values["messages"]:
                        msg.pretty_print()
    except Exception as e:
        print(f"Exception in run: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main(argv):
    del argv  # Unused.
    asyncio.run(run())

if __name__ == "__main__":
    app.run(main)
