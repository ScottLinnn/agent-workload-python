import os
import sys
import asyncio
import traceback
from absl import app
from google.cloud import aiplatform as vertexai

from itinerary_planner.langgraph.agent import itinerary_langgraph_agent

async def run():
    try:
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        config = {"configurable": {"thread_id": "session_langgraph_4"}}
        inputs = {"messages": [("user", "Plan a 3-day trip to Tokyo with a total budget of $1200.")]}

        print("Starting LangGraph runner...")
        async for chunk in itinerary_langgraph_agent.astream(inputs, config=config, stream_mode="updates"):
            for node, values in chunk.items():
                print(f"\n--- Node: {node} ---")
                if "messages" in values:
                    for msg in values["messages"]:
                        msg.pretty_print()
    except Exception as e:
        traceback.print_exc()
        sys.exit(1)

def main(argv):
    del argv  # Unused.
    asyncio.run(run())

if __name__ == "__main__":
    app.run(main)
