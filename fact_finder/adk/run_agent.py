import os
import sys
import asyncio

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'


from fact_finder.adk.agent import fact_finder_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._debug_output import print_event
from google.genai import types

async def main():
    runner = Runner(
        app_name="fact_finder",
        agent=fact_finder_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    final_result = ""
    async for event in runner.run_async(
        user_id="shuninglin",
        session_id="session_1",
        new_message=types.Content(
            parts=[types.Part(text="Identify the fictional character who breaks the fourth wall, is known for humor, and had a TV show between the 60s and 80s with fewer than 50 episodes.")]
        ),
    ):
        print_event(event)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_result += part.text

    # Save result for evaluation
    result_path = os.path.join(os.path.dirname(__file__), 'fact_finder_result.txt')
    with open(result_path, 'w') as f:
        f.write(final_result)
    print(f"Result saved to {result_path}")

if __name__ == "__main__":
    asyncio.run(main())
