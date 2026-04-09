"""Script to deploy the data science agent to Vertex AI Agent Engine."""

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
from data_science.adk.agent import supervisor_agent
import vertexai

def generate_random_id(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def prep_databases():
    project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
    random_id = generate_random_id()
    bucket_name = "experiment-data-science-agent-db-bucket"
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
        print("Continuing anyway, assuming permissions might be sufficient.")

    # Generate mock data
    from data_science.mock_data_gen import generate_mock_data
    generate_mock_data()
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_path, 'data')
    
    duckdb_path = os.path.join(data_dir, 'logistics_analytical.db')
    sqlite_path = os.path.join(data_dir, 'logistics_transactional.db')
    
    print(f"Uploading files to gs://{bucket_name}/{prefix}/")
    try:
        subprocess.run(
            ["gcloud", "storage", "cp", duckdb_path, f"gs://{bucket_name}/{prefix}/"],
            check=True
        )
        subprocess.run(
            ["gcloud", "storage", "cp", sqlite_path, f"gs://{bucket_name}/{prefix}/"],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Failed to upload files: {e}")
        raise e
        
    return bucket_name, prefix

async def main():
  vertexai.init(
      project=os.environ["GOOGLE_CLOUD_PROJECT"],
      location=os.environ["GOOGLE_CLOUD_LOCATION"],
  )

  bucket_name, prefix = prep_databases()

  print("Deploying data_science_agent to Vertex AI Agent Engine...")
  client = vertexai.Client()

  config = {
      "staging_bucket": f"gs://vertex-agent-engine-staging-ds-agent-{generate_random_id()}",
      "requirements": [
          "google-cloud-aiplatform[agent_engines,adk]",
          "google-genai",
          "python-dotenv",
          "cloudpickle",
          "pydantic",
          "duckdb",
          "pandas",
          "matplotlib",
          "seaborn",
          "numpy",
          "google-cloud-storage",
      ],
      "extra_packages": [
          "data_science",
      ],
      "display_name": "data_science_agent",
      "env_vars": {
          "DATA_BUCKET": bucket_name,
          "DATA_PREFIX": prefix,
      }
  }

  remote_agent = client.agent_engines.create(
      agent=supervisor_agent,
      config=config,
  )
  print("Successfully deployed Agent Engine!")
  print(f"Resource name: {remote_agent.api_resource.name}")
  print(f"Data bucket: {bucket_name}, Prefix: {prefix}")


if __name__ == "__main__":
  asyncio.run(main())
