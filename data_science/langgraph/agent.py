import os
os.environ["GOOGLE_CLOUD_PROJECT"] = "390454992652"
import sys
from typing import TypedDict, Annotated, Sequence, List
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# Add repo root to path if needed
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

# Project overridden at top

from data_science.langgraph.tools import query_sqlite, query_duckdb, python_repl, run_shell_command, download_from_gcs, upload_to_gcs

# Define the state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_agent: str
    data_context: str
    plot_paths: List[str]

# Define instructions matching ADK
DB_EXPERT_INSTRUCTION = """
You are a Database Expert. Your task is to query SQLite and DuckDB to answer user questions.
Use `query_sqlite` for transactional data and `query_duckdb` for analytical data.
You also have `download_from_gcs` and `upload_to_gcs` to download/upload files from/to GCS.
Return data in JSON or clear tabular format.
"""

DS_ANALYST_INSTRUCTION = """
You are a Data Analyst. Your task is to write Python code to analyze data and create visualizations.
Use `python_repl` to execute code.
Save any plots or result files to the 'langgraph_data_science_results' directory.
You create insights from data provided by the DB expert or supervisor.
If requested to write an answer to a file, use `python_repl` to do so.
"""

SUPERVISOR_INSTRUCTION = """
You are the Supervisor of a Multi-Agent Data Science System.
Your task is to solve complex user requests by delegating to specialized sub-agents.
You have access to:
- `db_expert`: For data retrieval and GCS operations.
- `ds_analyst`: For analysis and visualization.

Coordinate them to answer the user's request.
Respond in JSON format with two keys:
- "next_agent": One of ["db_expert", "ds_analyst", "FINISH"]
- "instruction": The instruction for the next agent, or the final answer for the user if "FINISH".

Your output must be ONLY the JSON object, with no other text, thinking, or markdown formatting around it.

CRITICAL INSTRUCTION:
When instructing sub-agents to perform actions involving GCS (download or upload), you MUST use the EXACT bucket name and prefix that `db_expert` discovered by reading the environment variables `DATA_BUCKET` and `DATA_PREFIX`. Do NOT assume or hallucinate bucket names. If you need to output the bucket and prefix at the end of your final response, use the EXACT values discovered by `db_expert`.
"""

def create_graph(llm):
    # Define sub-agents using create_react_agent
    db_agent = create_react_agent(
        llm,
        tools=[query_sqlite, query_duckdb, run_shell_command, download_from_gcs, upload_to_gcs],
        prompt=DB_EXPERT_INSTRUCTION
    )

    ds_agent = create_react_agent(
        llm,
        tools=[python_repl],
        prompt=DS_ANALYST_INSTRUCTION
    )

    # Define nodes for the graph
    async def supervisor_node(state: AgentState):
        print("\n--- Supervisor Node ---")
        messages = state["messages"]
        
        system_message = SystemMessage(content=SUPERVISOR_INSTRUCTION)
        json_llm = llm.bind(response_mime_type="application/json")
        res = await json_llm.ainvoke([system_message] + list(messages))
        
        content = res.content
        print(f"Supervisor raw output: {content}")
        
        import json
        next_agent = "FINISH"
        instruction = str(content)
        
        candidates = []
        if isinstance(content, list):
            candidates = [c for c in content if isinstance(c, str)]
        else:
            candidates = [content]

        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            
            # Try to extract JSON if wrapped in code blocks
            text_to_parse = candidate
            if "```json" in text_to_parse:
                 text_to_parse = text_to_parse.split("```json")[1].split("```")[0].strip()
                 
            try:
                parsed = json.loads(text_to_parse)
                next_agent = parsed.get("next_agent", "FINISH")
                instruction = parsed.get("instruction", "")
                print(f"Successfully parsed supervisor JSON.")
                break # Found a valid one
            except json.JSONDecodeError:
                # Try to find JSON object by finding brackets
                start = candidate.find('{')
                end = candidate.rfind('}')
                if start != -1 and end != -1 and end > start:
                    bracket_text = candidate[start:end+1]
                    try:
                        parsed = json.loads(bracket_text)
                        next_agent = parsed.get("next_agent", "FINISH")
                        instruction = parsed.get("instruction", "")
                        print(f"Successfully parsed supervisor JSON by finding brackets.")
                        break
                    except json.JSONDecodeError:
                        pass
                
                # Try parsing the whole candidate if it didn't have ```json but might be raw JSON
                try:
                    parsed = json.loads(candidate.strip())
                    next_agent = parsed.get("next_agent", "FINISH")
                    instruction = parsed.get("instruction", "")
                    print(f"Successfully parsed supervisor JSON directly.")
                    break
                except json.JSONDecodeError:
                     continue

        return {
            "messages": [AIMessage(content=f"Supervisor thought: Route to {next_agent}. Instruction: {instruction}")],
            "current_agent": next_agent
        }

    async def db_agent_node(state: AgentState):
        print("\n--- DB Agent Node ---")
        last_message = state["messages"][-1].content
        instruction = last_message
        if "Instruction:" in last_message:
            instruction = last_message.split("Instruction:")[1].strip()

        res = await db_agent.ainvoke({"messages": [HumanMessage(content=instruction)]})
        
        return {
            "messages": [AIMessage(content=f"DB Agent Result: {res['messages'][-1].content}")],
            "data_context": res['messages'][-1].content,
            "current_agent": "supervisor"
        }

    async def ds_agent_node(state: AgentState):
        print("\n--- DS Agent Node ---")
        last_message = state["messages"][-1].content
        instruction = last_message
        if "Instruction:" in last_message:
            instruction = last_message.split("Instruction:")[1].strip()

        prompt = f"Instruction: {instruction}\n\nData Context:\n{state.get('data_context', '')}"
        res = await ds_agent.ainvoke({"messages": [HumanMessage(content=prompt)]})
        
        return {
            "messages": [AIMessage(content=f"DS Agent Result: {res['messages'][-1].content}")],
            "current_agent": "supervisor"
        }

    # Define Router
    def router(state: AgentState):
        return state["current_agent"]

    # Build the graph
    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("db_expert", db_agent_node)
    workflow.add_node("ds_analyst", ds_agent_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        router,
        {
            "db_expert": "db_expert",
            "ds_analyst": "ds_analyst",
            "FINISH": END
        }
    )

    workflow.add_edge("db_expert", "supervisor")
    workflow.add_edge("ds_analyst", "supervisor")

    return workflow.compile()

# Default LLM for local testing
default_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT'),
    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

compiled_graph = create_graph(default_llm)

class MyCustomLanggraphAgent:
    def __init__(self, model, runnable_builder, **kwargs):
        self._model = model
        self._runnable_builder = runnable_builder
        self._kwargs = kwargs
        self._runnable = None

    def set_up(self):
        self._runnable = self._runnable_builder(self._model, **self._kwargs)

    def query(self, input, config=None, **kwargs):
        from langchain_core.load import dump as langchain_core_load_dump
        from langchain_core.messages import HumanMessage
        import asyncio
        import nest_asyncio
        nest_asyncio.apply()
        
        if isinstance(input, str):
            input = {"messages": [HumanMessage(content=input)]}
        elif isinstance(input, dict) and "input" in input and "messages" not in input:
            input = {"messages": [HumanMessage(content=input["input"])]}
            
        if not self._runnable:
            self.set_up()
        
        response = asyncio.run(self._runnable.ainvoke(input=input, config=config, **kwargs))
        
        return langchain_core_load_dump.dumpd(response)
