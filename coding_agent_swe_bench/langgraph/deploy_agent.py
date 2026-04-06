"""Script to deploy the LangGraph coding agent to Vertex AI Agent Engine."""

import asyncio
import os
import sys
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
from coding_agent_swe_bench.langgraph.agent import coding_agent_langgraph
import vertexai
from vertexai import agent_engines


async def main():
  vertexai.init(
      project=os.environ["GOOGLE_CLOUD_PROJECT"],
      location=os.environ["GOOGLE_CLOUD_LOCATION"],
  )

  print("Deploying coding_agent_swe_bench (LangGraph) to Vertex AI Agent Engine...")
  client = vertexai.Client()

  deploy_key = os.environ.get("GITHUB_DEPLOY_KEY")

  config = {
      "staging_bucket": "gs://vertex-agent-engine-staging-langgraph-coding-agent",
      "requirements": [
          "google-cloud-aiplatform[agent_engines,langchain]",
          "langgraph",
          "langchain-google-vertexai",
          "python-dotenv",
          "cloudpickle",
          "pydantic",
          "duckduckgo-search",
          "beautifulsoup4",
      ],
      "extra_packages": [
          "coding_agent_swe_bench",
      ],
      "display_name": "coding_agent_swe_bench_langgraph",
  }

  if deploy_key:
    config["env_vars"] = {"GITHUB_DEPLOY_KEY": deploy_key}

  remote_agent = client.agent_engines.create(
      agent=coding_agent_langgraph,
      config=config,
  )
  print("Successfully deployed Agent Engine!")
  print(f"Resource name: {remote_agent.api_resource.name}")


if __name__ == "__main__":
  asyncio.run(main())
