import asyncio
import os
import sys

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

async def main():
    prompt = """
    Find the most popular product among users aged 20-30 in the 'North' region.
    The data is split across two databases that are ALREADY present locally. Do NOT try to download them from GCS.
    
    1. SQLite database (queried via `query_sqlite`):
       - `users` table: `id`, `name`, `age`, `region`
       - `orders` table: `id`, `user_id`, `order_date`
       
    2. DuckDB database (queried via `query_duckdb`):
       - `order_details` table: `order_id`, `product_id`, `quantity`
       - `products` table: `id`, `name`, `category`
       
    You MUST use the multi-agent system as follows:
    1. Delegate to `db_expert` to query both databases and find the most popular product and its quantity.
       - Use `query_sqlite` to query user and order data.
       - Use `query_duckdb` to query product and order details data.
    2. Delegate to `ds_analyst` to write the answer in the format 'product name: <name>, quantity: <total_quantity>' to 'langgraph_data_science_results/answer.txt' using `python_repl`.
    3. The Supervisor should summarize the result and finish.
    """

    print("=== Running LangGraph Data Science Multi-Agent System ===")
    
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

if __name__ == "__main__":
    asyncio.run(main())
