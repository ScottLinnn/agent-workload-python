import os
import sys
import asyncio

os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = '1'
os.environ['GOOGLE_CLOUD_LOCATION'] = 'us-central1'

from coding_agent.adk.agent import coding_agent, WORKSPACE_FILES, GIT_LOG
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._debug_output import print_event
from google.genai import types

async def main():
    runner = Runner(
        app_name="coding_agent",
        agent=coding_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    async for event in runner.run_async(
        user_id="shuninglin",
        session_id="session_1",
        new_message=types.Content(
            parts=[types.Part(text="Go to the PerfKitBenchmarker issues page, pick an issue, and attempt to resolve it in our local clone in the current directory.")]
        ),
    ):
        print_event(event)

    print(f"\nFinal State of Workspace:")
    for path, content in WORKSPACE_FILES.items():
        print(f"--- {path} ---")
        print(content)
    
    print(f"\nGit Commits: {GIT_LOG}")

if __name__ == "__main__":
    asyncio.run(main())
