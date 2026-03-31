import os
import sys
import asyncio
import json

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'


from financial_model_updater.adk.agent import financial_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._debug_output import print_event
from google.genai import types

async def main():
    try:
        runner = Runner(
            app_name="financial_model_updater",
            agent=financial_agent,
            session_service=InMemorySessionService(),
            auto_create_session=True,
        )
        print("Starting runner...")
        async for event in runner.run_async(
            user_id="shuninglin",
            session_id="session_1",
            new_message=types.Content(
                parts=[types.Part(text="Process the Q4 revenue estimates from q4_data.txt, update the model.xlsx, recalculate IRR, and save the summary to summary.md.")]
            ),
        ):
            print_event(event)
    except Exception as e:
        print(f"Exception in main: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
