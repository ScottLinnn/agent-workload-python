import os
import sys
import asyncio
import re
import json

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'


from bug_triage.adk.agent import bug_triage_agent, SLACK_INBOX
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._debug_output import print_event
from google.genai import types

async def main():
    runner = Runner(
        app_name="bug_triage",
        agent=bug_triage_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    async for event in runner.run_async(
        user_id="shuninglin",
        session_id="session_1",
        new_message=types.Content(
            parts=[types.Part(text="Execute the complete bug triage workflow: 1. Fetch all high-priority GitHub issues using fetch_github_issues. 2. Summarize them. 3. Post the summaries to Slack channel #incident-response using post_to_slack.")]
        ),
    ):
        print_event(event)
    
    # Save SLACK_INBOX for evaluation
    payload_path = os.path.join(os.path.dirname(__file__), 'slack_payload.json')
    with open(payload_path, 'w') as f:
        json.dump(SLACK_INBOX, f)
    print(f"Slack payload saved to {payload_path}")

if __name__ == "__main__":
    asyncio.run(main())
