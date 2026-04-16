import os

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "1"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"

import json
import typing

# Try to import lancedb
try:
  import lancedb
  from lancedb.pydantic import LanceModel, Vector
except ImportError:
  lancedb = None

from google import genai
from google.genai import types

# Initialize client for Vertex AI
try:
  genai_client = genai.Client(vertexai=True, location="us-central1")
except Exception as e:
  genai_client = None
  print(f"Warning: Failed to initialize GenAI client: {e}")

def get_db_dir():
  DATA_BUCKET = os.environ.get("DATA_BUCKET")
  DATA_PREFIX = os.environ.get("DATA_PREFIX", "")

  if DATA_BUCKET:
    if DATA_PREFIX:
      return f"gs://{DATA_BUCKET}/{DATA_PREFIX}/langgraph_rag_agent_lancedb"
    else:
      return f"gs://{DATA_BUCKET}/langgraph_rag_agent_lancedb"
  else:
    return os.path.join(os.getcwd(), "langgraph_rag_agent_lancedb")


def _get_embedding(text: str) -> list[float]:
  """Get embeddings using Gemini API."""
  if not genai_client:
    # Fallback for testing or missing API key
    print("Warning: GenAI client not initialized. Returning dummy vector.")
    return [0.1] * 768

  try:
    response = genai_client.models.embed_content(
        model="text-embedding-004",  # Standard embedding model
        contents=text,
    )
    if hasattr(response, "embeddings") and response.embeddings:
      return response.embeddings[0].values
    elif isinstance(response, list) and len(response) > 0:
      return response[0]
    else:
      print(
          "Warning: Unexpected response structure from embed_content. Returning"
          " dummy vector."
      )
      return [0.1] * 768
  except Exception as e:
    print(f"Warning: Failed to get embedding: {e}. Returning dummy vector.")
    return [0.1] * 768


def vector_database_search(query: str, top_k: int = 1) -> str:
  """Searches the primary internal knowledge base for semantic matches.

  Args:
      query: The search query optimized for semantic matching.
      top_k: Number of chunks to retrieve (default: 1).

  Returns:
      JSON string of matching documents and their source metadata.
  """
  if not lancedb:
    return "Error: lancedb library not installed. Cannot perform vector search."

  try:
    db_dir = get_db_dir()
    if not db_dir.startswith("gs://"):
      os.makedirs(db_dir, exist_ok=True)
    db = lancedb.connect(db_dir)

    table_name = "documents"

    try:
      table = db.open_table(table_name)
    except Exception as e:
      return json.dumps({
          "error": (
              f"Table '{table_name}' not found in LanceDB. Please run"
              f" mock_data_gen.py to prepare the database. Details: {e}"
          )
      })

    # Perform search
    query_vector = _get_embedding(query)
    results = table.search(query_vector).limit(top_k).to_pandas()

    # Convert results to standard format
    output_results = []
    for _, row in results.iterrows():
      output_results.append({
          "content": row["content"],
          "metadata": (
              json.loads(row["metadata"])
              if isinstance(row["metadata"], str)
              else row["metadata"]
          ),
          "distance": float(row.get("_distance", 0)),
      })

    return json.dumps(output_results, default=str)

  except Exception as e:
    return json.dumps({"error": f"Vector Search Error: {e}"})


def evaluate_relevance(user_question: str, retrieved_text: str) -> str:
  """An internal tool the agent uses to grade the information it just retrieved against the original user question.

  Args:
      user_question: The core question being answered.
      retrieved_text: The text to evaluate.

  Returns:
      JSON object containing relevance evaluation.
  """
  if not genai_client:
    return json.dumps({
        "is_relevant": True,
        "missing_information": "GenAI client not initialized.",
        "suggested_next_query": "",
    })

  prompt = f"""
    You are an expert research assistant. Evaluate if the following retrieved text answers the user question.
    
    User Question: {user_question}
    Retrieved Text: {retrieved_text}
    
    Respond in JSON format with the following keys:
    - is_relevant: boolean, true if the text contains useful information related to the question, false otherwise.
    - missing_information: string, describe what information is missing to fully answer the question.
    - suggested_next_query: string, a suggested search query to find the missing information.
    
    Be strict. If the text only partially answers the question or points to another entity that needs to be looked up, state that it is incomplete and suggest the next query.
    """

  try:
    response = genai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text
  except Exception as e:
    print(f"Warning: Failed to evaluate relevance using Gemini: {e}")
    return json.dumps({
        "is_relevant": True,
        "missing_information": f"Gemini evaluation failed: {e}",
        "suggested_next_query": "",
    })


def web_search(search_term: str) -> str:
  """Executes a search on the public internet if the internal database fails to yield results.

  Args:
      search_term: The keyword-based search query.

  Returns:
      Snippets from top web results.
  """
  try:
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
      results = ddgs.text(search_term, max_results=5)
      output = []
      for r in results:
        output.append(
            {"title": r["title"], "url": r["href"], "snippet": r["body"]}
        )
      return json.dumps(output) if output else "No results found."
  except ImportError:
    return (
        "Search tool requires `duckduckgo-search` package. Please run `pip"
        " install duckduckgo-search`."
    )
  except Exception as e:
    return f"Web search tool failed: {e}"


def submit_final_answer(final_response: str, citations: list[str]) -> str:
  """Called strictly when the agent has gathered and verified all necessary information.

  Args:
      final_response: The comprehensive, well-formatted answer to the user.
      citations: The sources used to formulate the answer.

  Returns:
      Status message.
  """
  # Ensure framework + task in the name for resources
  results_dir = "langgraph_rag_agent_results"
  os.makedirs(results_dir, exist_ok=True)

  output_file = os.path.join(results_dir, "final_answer.json")

  result_data = {"final_response": final_response, "citations": citations}

  with open(output_file, "w") as f:
    json.dump(result_data, f, indent=2)

  DATA_BUCKET = os.environ.get("DATA_BUCKET")
  DATA_PREFIX = os.environ.get("DATA_PREFIX")

  if DATA_BUCKET:
    from google.cloud import storage

    try:
      storage_client = storage.Client()
      bucket = storage_client.bucket(DATA_BUCKET)
      blob_path = (
          f"{DATA_PREFIX}/final_answer.json" if DATA_PREFIX else "final_answer.json"
      )
      blob = bucket.blob(blob_path)
      blob.upload_from_filename(output_file)
      return f"Final answer submitted, saved to {output_file}, and uploaded to gs://{DATA_BUCKET}/{blob_path}."
    except Exception as e:
      return f"Final answer saved locally but failed to upload to GCS: {e}"

  return f"Final answer submitted and saved to {output_file}."


ALL_TOOLS = [
    vector_database_search,
    evaluate_relevance,
    web_search,
    submit_final_answer,
]
