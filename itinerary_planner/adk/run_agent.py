import os
import sys
import asyncio
import json

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'


from itinerary_planner.adk.agent import itinerary_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._debug_output import print_event
from google.genai import types

async def main():
    runner = Runner(
        app_name="itinerary_planner",
        agent=itinerary_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    itinerary_text = ""
    async for event in runner.run_async(
        user_id="shuninglin",
        session_id="session_1",
        new_message=types.Content(
            parts=[types.Part(text="Plan a 3-day itinerary for Tokyo with a total budget of $1200.")]
        ),
    ):
        print_event(event)
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    itinerary_text += part.text
    # Basic extraction
    try:
        json_start = itinerary_text.find('{')
        json_end = itinerary_text.rfind('}') + 1
        itinerary_json = json.loads(itinerary_text[json_start:json_end])
        itinerary_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        itinerary_path = os.path.join(itinerary_dir, 'itinerary.json')
        with open(itinerary_path, 'w') as f:
            json.dump(itinerary_json, f)
        print(f"Itinerary saved to {itinerary_path}")
    except Exception as e:
        print(f"Error extracting JSON: {e}")
        # Save raw response if JSON parse fails
        itinerary_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        raw_path = os.path.join(itinerary_dir, 'itinerary_raw.txt')
        with open(raw_path, 'w') as f:
            f.write(itinerary_text)
        print(f"Raw itinerary saved to {raw_path}")

if __name__ == "__main__":
    asyncio.run(main())
