import asyncio
import os
import sys
from absl import flags

# Set environment variables similar to ADK
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from langchain_core.messages import HumanMessage
from data_science.langgraph.agent import compiled_graph

FLAGS = flags.FLAGS
# Define flags to allow direct execution with flags
try:
    flags.DEFINE_boolean("remote", False, "Run agent remotely on Vertex AI.")
    flags.DEFINE_string("agent_engine_id", None, "Agent Engine resource ID for remote execution.")
except flags.DuplicateFlagError:
    pass

async def main(argv=None):
    try:
        remote = FLAGS.remote
        agent_engine_id = FLAGS.agent_engine_id
    except AttributeError:
        remote = False
        agent_engine_id = None

    data_bucket = os.environ.get("DATA_BUCKET", "experiment-data-science-agent-db-bucket")
    data_prefix = os.environ.get("DATA_PREFIX", "")

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
    2. Instruct `db_expert` to use `download_from_gcs` to download the database files from GCS using the bucket and prefix found in step 1. Do NOT use hardcoded values.
       - bucket: <value of DATA_BUCKET>, blob: <value of DATA_PREFIX>/logistics_analytical.db, file: logistics_analytical.db
       - bucket: <value of DATA_BUCKET>, blob: <value of DATA_PREFIX>/logistics_transactional.db, file: logistics_transactional.db
    3. Delegate to `db_expert` to query both databases and find the most popular product and its quantity.
    4. Delegate to `ds_analyst` to write the answer in the format 'product name: <name>, quantity: <total_quantity>' to 'langgraph_data_science_results/answer.txt' using `python_repl`.
    5. FINALLY, the Supervisor MUST instruct `db_expert` to use `upload_to_gcs` to upload the result file back to GCS using the same bucket and prefix found in step 1.
       - bucket: <value of DATA_BUCKET>, file: langgraph_data_science_results/answer.txt, blob: <value of DATA_PREFIX>/answer.txt
       
    If the database files are already present, you don't need to download them again.
    
    At the very end of your final response (Supervisor's final message), you MUST output the bucket name and prefix used in the following format:
    GCS_BUCKET: <value of DATA_BUCKET>
    GCS_PREFIX: <value of DATA_PREFIX>
    """

    print("=== Running LangGraph Data Science Multi-Agent System ===")

    if not remote:
        initial_state = {
            "messages": [HumanMessage(content=prompt)],
            "current_agent": "supervisor",
            "data_context": "",
            "plot_paths": []
        }

        async for output in compiled_graph.astream(initial_state):
            for node_name, state in output.items():
                print(f"\nNode finished: {node_name}")
                if "messages" in state and state["messages"]:
                    print(f"Output: {state['messages'][-1].content}")
                if "current_agent" in state:
                    print(f"Next agent: {state['current_agent']}")
    else:
        # Remote execution
        import vertexai
        
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        
        if not project_id:
             raise ValueError("GOOGLE_CLOUD_PROJECT must be set for remote execution")
             
        client = vertexai.Client(project=project_id, location=location)
        
        resource_name = f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_engine_id}"
        print(f"Querying remote agent: {resource_name}")
        
        remote_agent = client.agent_engines.get(name=resource_name)
        
        os.makedirs("langgraph_data_science_results", exist_ok=True)
        
        # SimpleLangGraphAgent has `query` method
        response = remote_agent.query(input=prompt)
        print(f"Response from remote agent:\n{response}")
        
        response_str = str(response)
        
        # Parse bucket and prefix from response if needed, similar to ADK
        import re
        bucket_matches = re.findall(r"GCS_BUCKET:\s*([a-zA-Z0-9_-]+)", response_str)
        prefix_matches = re.findall(r"GCS_PREFIX:\s*([a-zA-Z0-9_/-]+)", response_str)
        
        data_bucket = bucket_matches[-1] if bucket_matches else None
        data_prefix = prefix_matches[-1] if prefix_matches else ""
        
        if data_bucket:
            print(f"Parsed bucket from agent output: {data_bucket}")
        if data_prefix:
            print(f"Parsed prefix from agent output: {data_prefix}")

        if data_bucket:
            print(f"Downloading result from gs://{data_bucket}/{data_prefix}/answer.txt")
            try:
                import subprocess
                subprocess.run(
                    [
                        "gcloud",
                        "storage",
                        "cp",
                        f"gs://{data_bucket}/{data_prefix}/answer.txt",
                        "langgraph_data_science_results/answer.txt",
                    ],
                    check=True,
                )
                print("Successfully downloaded result from GCS.")
            except subprocess.CalledProcessError as e:
                print(f"Failed to download result from GCS: {e}")
        else:
            print("DATA_BUCKET not set and not found in output. Skipping automatic download.")

if __name__ == "__main__":
    # Initialize flags if not already initialized by something else
    try:
        FLAGS(sys.argv)
    except flags.UnparsedFlagAccessError:
        pass
    asyncio.run(main())
