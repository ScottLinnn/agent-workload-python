"""Script to deploy the RAG agent (LangGraph) to Vertex AI Agent Engine."""

import asyncio
import os
import sys
import random
import string
import subprocess
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
if "GOOGLE_CLOUD_LOCATION" not in os.environ:
    raise ValueError("GOOGLE_CLOUD_LOCATION environment variable must be set")
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
)

import vertexai
from agentic_rag.langgraph.agent import MyCustomLanggraphAgent

def generate_random_id(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def prep_databases():
    random_id = generate_random_id()
    bucket_name = "experiment-rag-agent-bucket"
    prefix = random_id
    
    print(f"Using bucket: {bucket_name} with prefix: {prefix}")

    # Grant access to Agent Engine service account (idempotent)
    sa_email = "service-390454992652@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    print(f"Granting storage.objectAdmin to {sa_email} on {bucket_name}")
    try:
        subprocess.run(
            ["gcloud", "storage", "buckets", "add-iam-policy-binding", f"gs://{bucket_name}",
             f"--member=serviceAccount:{sa_email}", "--role=roles/storage.objectAdmin"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to add IAM policy binding: {e}")

    # Generate mock data directly in GCS
    from agentic_rag.langgraph.mock_data_gen import generate_mock_data

    os.environ["DATA_BUCKET"] = bucket_name
    os.environ["DATA_PREFIX"] = prefix

    print(
        f"Generating LanceDB Data directly in GCS at gs://{bucket_name}/{prefix}/langgraph_rag_agent_lancedb"
    )
    generate_mock_data()

    return bucket_name, prefix

def my_runnable_builder(model, **kwargs):
    from agentic_rag.langgraph.agent import create_graph
    from langchain_google_genai import ChatGoogleGenerativeAI
    import os
    
    llm = ChatGoogleGenerativeAI(
        model=model,
        vertexai=True,
        project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
        location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
    )
    return create_graph(llm)

async def main():
    vertexai.init(
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    )

    bucket_name, prefix = prep_databases()

    print("Deploying rag_agent (LangGraph) to Vertex AI Agent Engine...")
    client = vertexai.Client()

    config = {
        "staging_bucket": f"gs://vertex-agent-engine-staging-rag-agent-{generate_random_id()}",
        "requirements": [
            "google-cloud-aiplatform[agent_engines]",
            "google-genai",
            "python-dotenv",
            "cloudpickle",
            "pydantic",
            "lancedb",
            "pyarrow",
            "google-cloud-storage",
            "pandas",
            "duckduckgo-search",
            "langgraph",
            "langchain",
            "langchain-google-genai",
            "langchain-core",
            "nest-asyncio",
        ],
        "extra_packages": [
            "agentic_rag",
        ],
        "display_name": "langgraph_rag_agent",
        "env_vars": {
            "DATA_BUCKET": bucket_name,
            "DATA_PREFIX": prefix,
        }
    }

    agent = MyCustomLanggraphAgent(
        model="gemini-2.5-flash",
        runnable_builder=my_runnable_builder,
    )

    remote_agent = client.agent_engines.create(
        agent=agent,
        config=config,
    )
    print("Successfully deployed Agent Engine!")
    print(f"Resource name: {remote_agent.api_resource.name}")
    print(f"Data bucket: {bucket_name}, Prefix: {prefix}")

if __name__ == "__main__":
    asyncio.run(main())
