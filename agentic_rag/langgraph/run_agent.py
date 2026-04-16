import asyncio
import os
import sys
from absl import flags

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from langchain_core.messages import HumanMessage
from agentic_rag.langgraph.agent import compiled_graph

FLAGS = flags.FLAGS
try:
    flags.DEFINE_boolean("remote", False, "Run agent remotely on Vertex AI")
    flags.DEFINE_string("agent_engine_id", None, "Vertex AI Reasoning Engine ID")
except flags.DuplicateFlagError:
    pass

async def main(argv=None):
    prompt = (
        "What is the exact battery capacity (in mAh) of the drone deployed for"
        " 'Operation Night Owl'?\n\nIMPORTANT: In your final response, you MUST"
        " state the GCS path where you saved your final answer (as returned by the"
        " submit_final_answer tool) in the format: GCS_PATH: gs://..."
    )

    print("=== Running LangGraph RAG Agent ===")

    try:
        # Parse flags if not already parsed
        FLAGS(sys.argv)
    except flags.UnparsedFlagAccessError:
        pass

    remote = FLAGS.remote
    agent_engine_id = FLAGS.agent_engine_id

    if not remote:
        initial_state = {
            "messages": [HumanMessage(content=prompt)]
        }

        async for output in compiled_graph.astream(initial_state):
            for node_name, state in output.items():
                print(f"\nNode finished: {node_name}")
                if "messages" in state and state["messages"]:
                    print(f"Output: {state['messages'][-1].content}")
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
        
        # Ensure framework + task in the name for resources
        results_dir = "langgraph_rag_agent_results"
        os.makedirs(results_dir, exist_ok=True)
        
        # SimpleLangGraphAgent has `query` method
        response = remote_agent.query(input=prompt)
        print(f"Response from remote agent:\n{response}")
        
        response_str = str(response)
        
        # Parse GCS path from response if needed
        import re
        gcs_path_matches = re.findall(r"GCS_PATH:\s*(gs://[a-zA-Z0-9_-]+/[\w./-]+)", response_str)
        gcs_path = gcs_path_matches[-1] if gcs_path_matches else None
        
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
                        os.path.join(results_dir, "final_answer.json"),
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
