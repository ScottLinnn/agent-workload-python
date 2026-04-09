import asyncio
import os
import sys

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from absl import flags

FLAGS = flags.FLAGS


def print_event_full(
    event, *, verbose: bool = False, log_file: str = None
) -> None:
  """Print an event to stdout in a user-friendly format, without truncation."""
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
          msg = (
              f"{event.author} > [Calling tool:"
              f" {part.function_call.name}("
              f"{part.function_call.args})]"
          )
          print(msg)
          if log_file:
            with open(log_file, "a") as f:
              f.write(msg + "\n")
        elif part.function_response:
          msg = (
              f"{event.author} > [Tool result:"
              f" {part.function_response.response}]"
          )
          print(msg)
          if log_file:
            with open(log_file, "a") as f:
              f.write(msg + "\n")
        elif part.executable_code:
          lang = part.executable_code.language or "code"
          print(f"{event.author} > [Executing {lang} code...]")
        elif part.code_execution_result:
          output = part.code_execution_result.output or "result"
          print(f"{event.author} > [Code output: {output}]")
        elif part.inline_data:
          mime_type = part.inline_data.mime_type or "data"
          print(f"{event.author} > [Inline data: {mime_type}]")
        elif part.file_data:
          uri = part.file_data.file_uri or "file"
          print(f"{event.author} > [File: {uri}]")

  flush_text()


from google.genai import types

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
  sys.path.append(ROOT_PATH)

from data_science.adk.agent import supervisor_agent


async def main():
  try:
    remote = FLAGS.remote
    agent_engine_id = FLAGS.agent_engine_id
  except AttributeError:
    # Fallback for direct run without flags initialized
    remote = False
    agent_engine_id = None

  prompt = """
    Find the most popular product among users aged 20-30 in the 'North' region.
    The data is split across two databases:
    
    1. SQLite database (queried via `query_sqlite`):
       - `users` table: `id`, `name`, `age`, `region`
       - `orders` table: `id`, `user_id`, `order_date`
       
    2. DuckDB database (queried via `query_duckdb`):
       - `order_details` table: `order_id`, `product_id`, `quantity`
       - `products` table: `id`, `name`, `category`
       
    You MUST use the multi-agent system as follows:
    1. The Supervisor MUST FIRST instruct `db_expert` to determine the GCS bucket and prefix by reading the environment variables `DATA_BUCKET` and `DATA_PREFIX` (you can use `run_shell_command` with `echo $DATA_BUCKET` and `echo $DATA_PREFIX`).
    2. Instruct `db_expert` to use `download_from_gcs` to download the database files from GCS using the bucket and prefix found:
       - bucket: <value of DATA_BUCKET>, blob: <value of DATA_PREFIX>/logistics_analytical.db, file: logistics_analytical.db
       - bucket: <value of DATA_BUCKET>, blob: <value of DATA_PREFIX>/logistics_transactional.db, file: logistics_transactional.db
    3. Delegate to `db_expert` to query both databases and find the most popular product and its quantity.
    4. Delegate to `ds_analyst` to write the answer in the format 'product name: <name>, quantity: <total_quantity>' to 'adk_data_science_results/answer.txt' using `python_repl`.
    5. FINALLY, the Supervisor MUST instruct `db_expert` to use `upload_to_gcs` to upload the result file back to GCS using the same bucket and prefix:
       - bucket: <value of DATA_BUCKET>, file: adk_data_science_results/answer.txt, blob: <value of DATA_PREFIX>/answer.txt
       
    If the database files are already present, you don't need to download them again.
    
    At the very end of your final response (Supervisor's final message), you MUST output the bucket name and prefix used in the following format:
    GCS_BUCKET: <bucket_name>
    GCS_PREFIX: <prefix>
    """

  print("=== Running Data Science Multi-Agent System ===")

  if not remote:
    runner = Runner(
        app_name="data_science_system",
        agent=supervisor_agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    async for event in runner.run_async(
        user_id="user_researcher",
        session_id="session_ds_1",
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
        name=f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
    )

    os.makedirs("adk_data_science_results", exist_ok=True)
    log_file = "adk_data_science_results/tool_calls.log"
    import datetime

    with open(log_file, "w") as f:
      f.write(f"Log started at: {datetime.datetime.now()}\n")

    accumulated_output = []
    async for event in adk_app.async_stream_query(
        user_id="user_researcher",
        message=prompt,
    ):
      if isinstance(event, dict):
        event = Event.model_validate(event)
      print_event_full(event, verbose=True, log_file=log_file)

      if event.content and event.content.parts:
        for part in event.content.parts:
          if part.text:
            accumulated_output.append(part.text)

    full_text = "".join(accumulated_output)

    data_bucket = os.environ.get("DATA_BUCKET")
    data_prefix = os.environ.get("DATA_PREFIX", "")

    if not data_bucket:
      import re

      bucket_match = re.search(r"GCS_BUCKET:\s*([^\s\n]+)", full_text)
      prefix_match = re.search(r"GCS_PREFIX:\s*([^\s\n]+)", full_text)
      if bucket_match and prefix_match:
        data_bucket = bucket_match.group(1)
        data_prefix = prefix_match.group(1)
        print(f"Parsed bucket from agent output: {data_bucket}")
        print(f"Parsed prefix from agent output: {data_prefix}")

    if data_bucket:
      print(
          f"Downloading result from gs://{data_bucket}/{data_prefix}/answer.txt"
      )
      try:
        import subprocess

        subprocess.run(
            [
                "gcloud",
                "storage",
                "cp",
                f"gs://{data_bucket}/{data_prefix}/answer.txt",
                "adk_data_science_results/answer.txt",
            ],
            check=True,
        )
        print("Successfully downloaded result from GCS.")
      except subprocess.CalledProcessError as e:
        print(f"Failed to download result from GCS: {e}")
    else:
      print(
          "DATA_BUCKET not set on client side. Skipping automatic download of"
          " result from GCS."
      )


if __name__ == "__main__":
  asyncio.run(main())
