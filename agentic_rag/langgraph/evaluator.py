"""Evaluator script for LangGraph RAG Agent."""

import json
import os
import sys

def evaluate():
  """Evaluates the results of the LangGraph RAG agent."""
  # Check if langgraph_rag_agent_results directory exists
  results_dir = os.path.join(os.getcwd(), "langgraph_rag_agent_results")
  if not os.path.exists(results_dir):
    print(f"FAILED: Results directory not found at {results_dir}")
    return False

  # Check if final_answer.json exists
  answer_path = os.path.join(results_dir, "final_answer.json")
  if not os.path.exists(answer_path):
    print(f"FAILED: final_answer.json not found at {answer_path}")
    return False

  # Verify content
  try:
    with open(answer_path, "r") as f:
      data = json.load(f)
  except (IOError, json.JSONDecodeError) as e:
    print(f"FAILED: Failed to parse final_answer.json: {e}")
    return False

  final_response = data.get("final_response", "")
  print(f"Info: final_response content:\n{final_response}")

  # We expect the answer to mention AeroScout X-4, Model LS-900, and 8500mAh (or 8500 mAh)
  expected_terms = ["AeroScout X-4", "Model LS-900"]
  missing_terms = [
      term for term in expected_terms if term not in final_response
  ]

  if "8500mAh" not in final_response and "8500 mAh" not in final_response:
    missing_terms.append("8500mAh")

  if not missing_terms:
    print("PASSED: RAG evaluation successful. Found all expected terms.")
    return True
  else:
    print(f"FAILED: final_response is missing expected terms: {missing_terms}")
    return False

if __name__ == "__main__":
  if evaluate():
    sys.exit(0)
  else:
    sys.exit(1)
