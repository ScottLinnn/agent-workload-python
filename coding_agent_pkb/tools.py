import os
import glob
import re
import subprocess
import typing
import json
import urllib.request

WORKSPACE_BASE = os.environ.get("WORKSPACE_BASE", os.getcwd())

def _ensure_strict_cwd(cwd: str) -> str:
    """Verifies that the target cwd is within the allowed workspace."""
    abs_cwd = os.path.abspath(cwd)
    if not abs_cwd.startswith(WORKSPACE_BASE):
        raise ValueError(f"Security error: Command execution outside '{WORKSPACE_BASE}' is forbidden. Attempted: {abs_cwd}")
    return abs_cwd

def read_file(path: str) -> str:
    """Read a file."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def create_file(path: str, content: str) -> str:
    """Create a new file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        return "File created successfully."
    except Exception as e:
        return f"Error creating file: {e}"

def edit_code(path: str, search_string: str, replace_string: str) -> str:
    """Edit code by replacing a search string with a replace string."""
    try:
        with open(path, 'r') as f:
            content = f.read()
        if search_string not in content:
            return "Search string not found in file."
        with open(path, 'w') as f:
            f.write(content.replace(search_string, replace_string, 1))
        return "File edited successfully."
    except Exception as e:
        return f"Error editing file: {e}"

def rename_file(old_path: str, new_path: str) -> str:
    """Rename and reorganize a file."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(new_path)), exist_ok=True)
        os.rename(old_path, new_path)
        return "File renamed successfully."
    except Exception as e:
        return f"Error renaming file: {e}"

def find_files(pattern: str, cwd: str = ".") -> str:
    """Find files by glob pattern."""
    try:
        cwd = _ensure_strict_cwd(cwd)
        files = glob.glob(f"{cwd}/**/{pattern}", recursive=True)
        return "\n".join(files) if files else "No files found."
    except Exception as e:
        return f"Error finding files: {e}"

def search_content(regex: str, cwd: str = ".") -> str:
    """Search content with regex."""
    try:
        cwd = _ensure_strict_cwd(cwd)
        res = subprocess.run(["grep", "-rnE", regex, cwd], capture_output=True, text=True)
        return res.stdout if res.stdout else "No matches found."
    except Exception as e:
        return f"Error searching content: {e}"

def run_shell_command(cmd: str, cwd: str = ".") -> str:
    """Run shell commands, start servers, run tests, use git. 
    Strictly enforced to be within the allowed workspace.
    """
    try:
        cwd = _ensure_strict_cwd(cwd)
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
        return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\nEXIT CODE: {res.returncode}"
    except Exception as e:
        return f"Error running shell command: {e}"

def search_web(query: str) -> str:
    """Fetches web snippets using DuckDuckGo (requires duckduckgo-search pypi package)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
            output = []
            for r in results:
                output.append(f"Title: {r['title']}\nURL: {r['href']}\nSnippet: {r['body']}\n---")
            return "\n".join(output) if output else "No results found."
    except ImportError:
        return "Search tool requires `duckduckgo-search` package in standalone mode. Please run `pip install duckduckgo-search`."
    except Exception as e:
        return f"Web search tool failed: {e}"

def fetch_webpage(url: str) -> str:
    """Browses a web page by URL to fetch its content."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # Use BeautifulSoup to get cleaner text content if available
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')
                # Remove scripts, styles and other irrelevant content
                for element in soup(['script', 'style', 'header', 'footer', 'nav']):
                    element.decompose()
                text = soup.get_text(separator=' ', strip=True)
                return text[:5000]
            except ImportError:
                # Basic HTML stripping as fallback
                text = re.sub(r'<[^>]+>', ' ', html)
                return text[:5000]
                
    except Exception as e:
        return f"Fetch tool failed: {e}"

ALL_TOOLS = [
    read_file, create_file, edit_code, rename_file, 
    find_files, search_content, run_shell_command, 
    search_web, fetch_webpage
]
