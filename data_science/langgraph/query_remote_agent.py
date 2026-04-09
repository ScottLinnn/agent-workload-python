import os
import sys
import asyncio
import vertexai

# Add repo root to path
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_CLOUD_PROJECT"] = "390454992652"

async def main():
    engine_id = "3887600986688061440"
    project_id = "390454992652"
    location = "us-central1"
    
    resource_name = f"projects/{project_id}/locations/{location}/reasoningEngines/{engine_id}"
    
    print(f"Querying Reasoning Engine: {resource_name}")
    
    client = vertexai.Client()
    
    try:
        remote_agent = client.agent_engines.get(name=resource_name)
        
        prompt = "Find the most popular product among users aged 20-30 in the 'North' region."
        
        print(f"Sending prompt: {prompt}")
        
        # Reasoning Engine resources usually have methods mapping to the wrapped object methods.
        # Since we wrapped it in SimpleLangGraphAgent which has `query` method,
        # we should be able to call `remote_agent.query(input=...)`.
        
        response = remote_agent.query(input=prompt)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Error querying agent: {e}")

if __name__ == "__main__":
    asyncio.run(main())
