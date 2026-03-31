import sys
import os
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

def google_search(query: str) -> list[str]:
    """Mock search tool for public repo.
    
    Replace this with a real search tool (e.g. Google Custom Search API) 
    when deploying in a public environment.
    """
    print(f"[STUB] Search query: {query}")
    # Simulating returning some URLs
    return [
        "https://example.com/stub-result-1",
        "https://example.com/stub-result-2"
    ]

def load_web_page(url: str) -> str:
    """Mock load web page tool.
    
    Returns a simulated page content to satisfy the facts.
    """
    print(f"Reading webpage: {url}")
    if "stub-result-1" in url:
        return """
        List of characters who break the fourth wall:
        1. Frank Drebin (Police Squad!) - Known for absurdist humor in the 1982 show.
           Police Squad! had only 6 episodes.
        """
    return "Page not found."

# Initialize the model using Vertex AI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

# Define tools
tools = [google_search, load_web_page]

# Create the LangGraph ReAct agent
system_message = """
You are a professional trivia investigator with access to the real web. 
Your goal is to answer a constrained trivia question by following these steps:
1. Search for key terms in the question using the google_search tool.
2. From the search results, identify candidate characters and TV shows.
3. Use the load_web_page tool to visit relevant websites and verify the constraints:
   - Fictional character who breaks the fourth wall.
   - Known for humor.
   - Had a TV show aired between the 1960s and 1980s.
   - The show has fewer than 50 episodes.
4. Provide the final answer clearly with a brief justification and mention the source URLs.

You MUST use the google_search and load_web_page tools to gather real evidence.
"""

fact_finder_real_web_langgraph_agent = create_react_agent(llm, tools, checkpointer=MemorySaver(), prompt=system_message)
