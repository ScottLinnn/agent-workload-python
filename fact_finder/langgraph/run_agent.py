import os
import sys
import asyncio
from absl import app
from google.cloud import aiplatform as vertexai

from fact_finder.langgraph.agent import fact_finder_langgraph_agent

async def run():
    try:
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        config = {"configurable": {"thread_id": "session_langgraph_2"}}
        inputs = {"messages": [("user", "Which fictional character, known for direct comedic addresses to the audience, appeared in a humor-focused TV show that aired between 1960 and 1989 and had fewer than 50 episodes?")]}

        print("Starting LangGraph runner...")
        async for chunk in fact_finder_langgraph_agent.astream(inputs, config=config, stream_mode="updates"):
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
