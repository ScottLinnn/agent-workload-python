import sys
import os




from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Mock search results (shared logic)
MOCK_SEARCH_RESULTS = {
    "fictional character breaks fourth wall humor TV show 1960s-1980s fewer than 50 episodes": [
        "https://example.com/top-fourth-wall-breakers",
        "https://example.com/cult-comedy-shows-80s"
    ],
    "Police Squad! TV show episodes": [
        "https://example.com/police-squad-wiki"
    ],
    "The Young Ones Rick fourth wall": [
        "https://example.com/young-ones-rick-analysis"
    ]
}

MOCK_PAGES = {
    "https://example.com/top-fourth-wall-breakers": """
        List of characters who break the fourth wall:
        1. Deadpool (Movies)
        2. Frank Drebin (Police Squad!) - Known for absurdist humor in the 1982 show.
        3. Rick (The Young Ones) - Anarchic comedy, breaks the wall frequently.
        4. Zack Morris (Saved by the Bell) - 90s.
    """,
    "https://example.com/police-squad-wiki": """
        Police Squad! is a television comedy series broadcast in 1982. 
        It stars Leslie Nielsen as Detective Frank Drebin. 
        The show was famously cancelled after only 6 episodes.
    """,
    "https://example.com/young-ones-rick-analysis": """
        Rick in 'The Young Ones' (1982-1984) is a self-proclaimed 'People's Poet'. 
        He often addresses the audience directly, breaking the fourth wall for comedic effect.
        The series had a total of 12 episodes across two series.
    """
}

def search_web(query: str) -> list[str]:
    """Search the web for a given query and return a list of URLs.
    
    Args:
        query: The search query string.
        
    Returns:
        A list of simulated URL results.
    """
    print(f"Searching for: {query}")
    query_lower = query.lower()
    if "fourth wall" in query_lower or "4th wall" in query_lower:
        return MOCK_SEARCH_RESULTS["fictional character breaks fourth wall humor TV show 1960s-1980s fewer than 50 episodes"]
    if "police squad" in query_lower or "drebin" in query_lower:
        return MOCK_SEARCH_RESULTS["Police Squad! TV show episodes"]
    if "young ones" in query_lower or "rick" in query_lower:
        return MOCK_SEARCH_RESULTS["The Young Ones Rick fourth wall"]
    return ["https://example.com/no-results"]

def read_webpage(url: str) -> str:
    """Read and return the content of a webpage.
    
    Args:
        url: The URL of the webpage to read.
        
    Returns:
        The text content of the webpage.
    """
    print(f"Reading webpage: {url}")
    return MOCK_PAGES.get(url, "Page not found.")

# Initialize the model using Vertex AI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

# Define tools
tools = [search_web, read_webpage]

# Create the LangGraph ReAct agent
system_message = """
You are a professional trivia investigator. 
Your goal is to answer a constrained trivia question by following these steps:
1. Search for key terms in the question.
2. Identify candidate characters and TV shows.
3. Verify the constraints: breaks fourth wall, humor, aired 1960s-1980s, fewer than 50 episodes.
4. Provide the final answer clearly with a brief justification.

Use the search_web and read_webpage tools as needed.
"""

fact_finder_langgraph_agent = create_react_agent(llm, tools, checkpointer=MemorySaver(), prompt=system_message)
