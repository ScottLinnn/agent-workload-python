import os
import sys


def evaluate():
  base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  data_dir = os.path.join(base_path, "data")
  duckdb_path = os.path.join(data_dir, "logistics_analytical.db")

  # Check if DuckDB file exists
  if not os.path.exists(duckdb_path):
    print(f"FAILED: DuckDB database file not found at {duckdb_path}")
    return False

  # Check if langgraph_data_science_results directory exists
  results_dir = os.path.join(os.getcwd(), "langgraph_data_science_results")
  if not os.path.exists(results_dir):
    print(f"FAILED: Results directory not found at {results_dir}")
    return False

  # Check if answer.txt exists
  answer_path = os.path.join(results_dir, "answer.txt")
  if not os.path.exists(answer_path):
    print(f"FAILED: answer.txt not found at {answer_path}")
    return False

  # Verify content of answer.txt
  with open(answer_path, "r") as f:
    content = f.read()

  print(f"Info: answer.txt content:\n{content}")

  # We expect 'SuperWidget' and quantity '8' (or at least SuperWidget)
  if "SuperWidget" in content and "8" in content:
    print(
        "PASSED: Data Science evaluation successful. Found expected answer."
    )
    return True
  elif "SuperWidget" in content:
    print(
        "PASSED: Data Science evaluation successful. Found expected product but maybe not quantity."
    )
    return True
  else:
    print(
        f"FAILED: answer.txt does not contain expected answer 'SuperWidget'. Content: {content}"
    )
    return False


if __name__ == "__main__":
  if evaluate():
    sys.exit(0)
  else:
    sys.exit(1)
