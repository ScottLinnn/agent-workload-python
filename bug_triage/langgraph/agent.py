import sys
import os
import json



from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Mock GitHub Data (shared logic)
MOCK_GITHUB_ISSUES = [
    {
        "id": 1,
        "title": "Database connection timeout in production",
        "description": "The worker nodes are experiencing intermittent 5xx errors due to DB timeouts when the load exceeds 10k RPS.",
        "label": "high-priority"
    },
    {
        "id": 2,
        "title": "Memory leak in video processing service",
        "description": "Memory usage grows linearly during long-running transcoding jobs, leading to OOM kills after 2 hours.",
        "label": "high-priority"
    },
    {
        "id": 3,
        "title": "Typo in FAQ page",
        "description": "Small typo in the third paragraph of the FAQ.",
        "label": "low-priority"
    }
]

# Shared state to capture Slack messages for evaluation
SLACK_INBOX = []

def fetch_github_issues(label: str) -> str:
    """Simulates fetching issues from GitHub filtered by label.
    
    Args:
        label: The label to filter issues by (e.g., 'high-priority').
        
    Returns:
        JSON string containing the issues.
    """
    print(f"Fetching GitHub issues with label: {label}")
    filtered = [i for i in MOCK_GITHUB_ISSUES if i['label'] == label]
    return json.dumps(filtered)

def post_to_slack(channel: str, message: str) -> str:
    """Simulates posting a message to a Slack channel.
    
    Args:
        channel: The name of the Slack channel.
        message: The content of the message.
        
    Returns:
        Success message.
    """
    print(f"Posting to Slack channel {channel}: {message}")
    SLACK_INBOX.append({"channel": channel, "message": message})
    return "Message posted successfully."

from langgraph.checkpoint.memory import MemorySaver

# Initialize the model using Vertex AI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

# Define tools
tools = [fetch_github_issues, post_to_slack]

# Create the LangGraph ReAct agent
# Use the same instruction as the ADK agent
system_message = """
You are a technical lead. Your task is:
1. Fetch all GitHub issues labeled 'high-priority' using fetch_github_issues.
2. For each issue, provide a concise technical summary of the problem.
3. Post the combined summaries to the '#incident-response' Slack channel using post_to_slack.

Format the Slack message professionally.
"""

bug_triage_langgraph_agent = create_react_agent(llm, tools, checkpointer=MemorySaver(), prompt=system_message)
