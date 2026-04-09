import os
import sys
from io import StringIO

# Import tools from ADK version to reuse them
from data_science.adk.tools import query_sqlite, query_duckdb, run_shell_command, download_from_gcs, upload_to_gcs

def python_repl(code: str) -> str:
    """Executes Python code in a local REPL (Sandboxed for data science task).
    Use this to run Pandas, Matplotlib, or Seaborn code.
    You should save plots to the 'langgraph_data_science_results' directory and return the path.
    
    Args:
        code: The Python code to execute.
        
    Returns:
        Standard output and error from the execution.
    """
    import sys
    from io import StringIO
    
    setup_code = """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

# Ensure results directory exists
os.makedirs('langgraph_data_science_results', exist_ok=True)
"""
    full_code = setup_code + "\n" + code

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = StringIO()
    redirected_error = StringIO()
    sys.stdout = redirected_output
    sys.stderr = redirected_error

    try:
        exec(full_code, {})
        stdout = redirected_output.getvalue()
        stderr = redirected_error.getvalue()
        return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
    except Exception as e:
        stdout = redirected_output.getvalue()
        stderr = redirected_error.getvalue()
        return f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nExecution Error: {e}"
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

ALL_TOOLS = [query_sqlite, query_duckdb, python_repl, run_shell_command, download_from_gcs, upload_to_gcs]
