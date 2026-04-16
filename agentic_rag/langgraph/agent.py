import os
import sys
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

# Add repo root to path if needed
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_PATH not in sys.path:
    sys.path.append(ROOT_PATH)

from agentic_rag.langgraph.tools import ALL_TOOLS

INSTRUCTIONS = """
You are an autonomous research agent. Your goal is to provide accurate, comprehensive answers by dynamically gathering information.

You operate in a loop:
1. You receive a question.
2. You use the `vector_database_search` tool to find information.
3. You MUST evaluate the retrieved information using the `evaluate_relevance` tool.
4. If `evaluate_relevance` indicates missing information, you must re-query the `vector_database_search` or use `web_search` with the `suggested_next_query`.
5. You repeat this process until you have all the facts required.
6. Once you are confident you have the complete picture, use the `submit_final_answer` tool to deliver the response.

Strict Rules:
- Never guess or hallucinate facts. If after multiple searches you cannot find the answer, use `submit_final_answer` to explain exactly what information is missing.
- You MUST ALWAYS use the `submit_final_answer` tool to provide your final response. Do NOT simply output the answer as text. This is critical for the system to save your results.
- Do not summarize intermediate steps to the user; only output the final answer via the `submit_final_answer` tool.
- Maintain a professional, objective tone.
"""

def create_graph(llm):
    return create_react_agent(
        llm,
        tools=ALL_TOOLS,
        prompt=INSTRUCTIONS
    )

# Default LLM for local testing
default_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=os.environ.get('GOOGLE_CLOUD_PROJECT', '390454992652'),
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
