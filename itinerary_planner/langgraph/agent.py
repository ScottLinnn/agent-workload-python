import sys
import os
import json



from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver


# Mock Data (import from adk subfolder)
from itinerary_planner.adk.data import FLIGHT_DATA, HOTEL_DATA, ATTRACTION_DATA

def search_flights(destination: str, dates: str) -> str:
    """Searches for flights to a destination on specific dates.
    
    Args:
        destination: Flight destination (e.g., 'Tokyo').
        dates: Dates to search for.
        
    Returns:
        JSON string of flight options.
    """
    print(f"Searching flights to {destination} for {dates}")
    return json.dumps(FLIGHT_DATA)

def search_hotels(destination: str, dates: str, budget: float) -> str:
    """Searches for hotels within a budget.
    
    Args:
        destination: Hotel destination.
        dates: Dates for stay.
        budget: Maximum total budget for the stay.
        
    Returns:
        JSON string of hotel options.
    """
    print(f"Searching hotels in {destination} for {dates} under {budget}")
    filtered = [h for h in HOTEL_DATA if h['price_per_night'] * 3 <= budget]
    return json.dumps(filtered)

def search_attractions(destination: str, budget: float) -> str:
    """Searches for attractions within a budget.
    
    Args:
        destination: City name.
        budget: Maximum budget for attractions.
        
    Returns:
        JSON string of attraction options.
    """
    print(f"Searching attractions in {destination} under {budget}")
    filtered = [a for a in ATTRACTION_DATA if a['fee'] <= budget]
    return json.dumps(filtered)

# Initialize the model using Vertex AI
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

# Define tools
tools = [search_flights, search_hotels, search_attractions]

# Create the LangGraph ReAct agent
system_message = """
You are a travel agent. Your task is to plan a 3-day trip to Tokyo with a total budget of $1200.
1. Search for round-trip flights from SFO to Tokyo for early May 2026.
2. Search for hotels in Tokyo for 3 nights. Ensure the check-in aligns with the flight arrival.
3. Search for attractions to visit.
4. Construct a JSON itinerary using exactly these keys:
   - 'flights': a dictionary with 'outbound' and 'return' keys, each containing 'id', 'airline', and 'price'.
   - 'hotel': a dictionary containing 'id', 'name', 'number_of_nights', and 'total_hotel_cost'.
   - 'attractions': a list of objects, each with 'name' and 'fee'.
   - 'grand_total_trip_cost': the sum of all costs.

Ensure all prices and totals are based on the search results and calculations.

Ensure all constraints are met.
"""

itinerary_langgraph_agent = create_react_agent(llm, tools, checkpointer=MemorySaver(), prompt=system_message)
