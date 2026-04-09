import asyncio
import os
import sys
import random
import string
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
  raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
if "GOOGLE_CLOUD_LOCATION" not in os.environ:
  raise ValueError("GOOGLE_CLOUD_LOCATION environment variable must be set")
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

import vertexai
from data_science.adk.deploy_agent import prep_databases

class SimpleLangGraphAgent:
    """A custom agent that wraps a LangGraph graph."""

    def __init__(self):
        pass

    def set_up(self):
        print("Setting up SimpleLangGraphAgent in cloud...")
        from data_science.langgraph.agent import compiled_graph
        self.graph = compiled_graph
        print("Graph compiled and loaded.")

    async def query(self, input: str) -> str:
        from langchain_core.messages import HumanMessage
        
        print(f"Querying agent with input: {input}")
        
        initial_state = {
            "messages": [HumanMessage(content=input)],
            "current_agent": "supervisor",
            "data_context": "",
            "plot_paths": []
        }
        
        print("Invoking graph...")
        result = await self.graph.ainvoke(initial_state)
        print("Graph invocation completed.")
        
        if "messages" in result and result["messages"]:
             return result["messages"][-1].content
        return "No result"

async def main():
  vertexai.init(
      project=os.environ["GOOGLE_CLOUD_PROJECT"],
      location=os.environ["GOOGLE_CLOUD_LOCATION"],
  )

  # Reuse database prep from ADK
  bucket_name, prefix = prep_databases()

  print("Deploying Custom LangGraph data_science_agent to Vertex AI Agent Engine...")
  client = vertexai.Client()

  def generate_random_id(length=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

  config = {
      "staging_bucket": f"gs://vertex-agent-engine-staging-lg-agent-{generate_random_id()}",
      "requirements": [
          "google-cloud-aiplatform[agent_engines]",
          "langgraph",
          "langchain-core",
          "langchain-google-genai",
          "langchain-google-vertexai",
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
      "display_name": "langgraph_data_science_agent",
      "env_vars": {
          "DATA_BUCKET": bucket_name,
          "DATA_PREFIX": prefix,
      }
  }

  agent = SimpleLangGraphAgent()

  remote_agent = client.agent_engines.create(
      agent=agent,
      config=config,
  )
  print("Successfully deployed Agent Engine!")
  print(f"Resource name: {remote_agent.api_resource.name}")
  print(f"Data bucket: {bucket_name}, Prefix: {prefix}")


if __name__ == "__main__":
  asyncio.run(main())
