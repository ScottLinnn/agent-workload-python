import os
import sys
import asyncio
import json

from google.cloud import aiplatform as vertexai
from absl import app
from bug_triage.langgraph.agent import bug_triage_langgraph_agent, SLACK_INBOX

async def run():
    try:
        vertexai.init(
            project=os.environ.get("GOOGLE_CLOUD_PROJECT"), 
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        )
        
        config = {"configurable": {"thread_id": "session_langgraph_1"}}
        inputs = {"messages": [("user", "Please fetch the high-priority issues from GitHub and post the summaries to Slack.")]}

        print("Starting LangGraph runner...")
        async for chunk in bug_triage_langgraph_agent.astream(inputs, config=config, stream_mode="updates"):
            for node, values in chunk.items():
                print(f"\n--- Node: {node} ---")
                if "messages" in values:
                    for msg in values["messages"]:
                        msg.pretty_print()
                        
        # Save SLACK_INBOX for evaluation in the adk folder
        # main.py expects it there for the evaluator
        adk_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "adk"))
        payload_path = os.path.join(adk_dir, 'slack_payload.json')
        with open(payload_path, 'w') as f:
            json.dump(SLACK_INBOX, f)
        print(f"\nSlack payload saved to {payload_path}")
    except Exception as e:
        print(f"Exception in run: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main(argv):
    asyncio.run(run())

if __name__ == "__main__":
    app.run(main)
