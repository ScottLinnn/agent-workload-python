import os
import sys

from google.adk.agents.llm_agent import Agent
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

from google.adk.tools.load_web_page import load_web_page

# The Trivia question:
# "Identify the fictional character who breaks the fourth wall, is known for humor,
#  and had a TV show between the 60s and 80s with fewer than 50 episodes."

fact_finder_agent = Agent(
    name="fact_finder_agent_real_web",
    description="An agent that can answer obscure trivia through real web search and scraping.",
    instruction="""
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
    """,
    model="gemini-2.5-flash", 
    tools=[
        google_search,
        load_web_page
    ]
)
