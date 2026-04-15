import asyncio
import os
import sys

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from absl import flags

FLAGS = flags.FLAGS
try:
  flags.DEFINE_boolean("remote", False, "Run agent remotely on Vertex AI")
  flags.DEFINE_string("agent_engine_id", None, "Vertex AI Reasoning Engine ID")
except flags.DuplicateFlagError:
  pass

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
  sys.path.append(ROOT_PATH)

from agentic_rag.adk.agent import rag_agent


def print_event_full(event, *, verbose: bool = False) -> None:
  """Print an event to stdout in a user-friendly format."""
  if not event.content or not event.content.parts:
    return

  text_buffer = []

  def flush_text() -> None:
    if text_buffer:
      combined_text = "".join(text_buffer)
      print(f"{event.author} > {combined_text}")
      text_buffer.clear()

  for part in event.content.parts:
    if part.text:
      text_buffer.append(part.text)
    else:
      flush_text()

      if verbose:
        if part.function_call:
          print(
              f"{event.author} > [Calling tool:"
              f" {part.function_call.name}({part.function_call.args})]"
          )
        elif part.function_response:
          print(
              f"{event.author} > [Tool result:"
              f" {part.function_response.response}]"
          )

  flush_text()


async def main():
  prompt = (
      "What is the exact battery capacity (in mAh) of the drone deployed for"
      " 'Operation Night Owl'?\n\nIMPORTANT: In your final response, you MUST"
      " state the GCS bucket and prefix where you saved your final answer in"
      " the format: GCS_PATH: gs://bucket/prefix/final_answer.json"
  )

  print("=== Running Agentic RAG Agent ===")

  try:
    # Parse flags if not already parsed
    FLAGS(sys.argv)
  except flags.UnparsedFlagAccessError:
    pass

  remote = FLAGS.remote
  agent_engine_id = FLAGS.agent_engine_id

  if not remote:
    runner = Runner(
        app_name="agentic_rag_system",
        agent=rag_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    async for event in runner.run_async(
        user_id="user_researcher",
        session_id="session_rag_1",
        new_message=types.Content(parts=[types.Part(text=prompt)]),
    ):
      print_event_full(event, verbose=True)
  else:
    # Remote execution
    import vertexai
    from google.adk.events.event import Event

    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.environ["GOOGLE_CLOUD_LOCATION"]

    client = vertexai.Client(project=project_id, location=location)
    adk_app = client.agent_engines.get(
        name=(
            f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
        )
    )

    os.makedirs("adk_rag_agent_results", exist_ok=True)

    gcs_path = None
    async for event in adk_app.async_stream_query(
        user_id="user_researcher",
        message=prompt,
    ):
      if isinstance(event, dict):
        event = Event.model_validate(event)
      print_event_full(event, verbose=True)

      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.function_response:
            response_text = str(part.function_response.response)
            if "uploaded to gs://" in response_text:
              import re
              match = re.search(r"(gs://[\w./-]+)", response_text)
              if match:
                gcs_path = match.group(1).rstrip(".")

    if gcs_path:
      print(f"Downloading result from GCS path: {gcs_path}")
      try:
        import subprocess

        subprocess.run(
            [
                "gcloud",
                "storage",
                "cp",
                gcs_path,
                "adk_rag_agent_results/final_answer.json",
            ],
            check=True,
        )
        print("Successfully downloaded result from GCS.")
      except subprocess.CalledProcessError as e:
        print(f"Failed to download result from GCS: {e}")
    else:
      print("Warning: GCS_PATH not found in agent response.")


if __name__ == "__main__":
  asyncio.run(main())
