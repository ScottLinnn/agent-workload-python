# Agentic Workload Python

This repository contains a collection of agentic workloads implemented using different frameworks (Google ADK and LangGraph). These workloads are designed to test and evaluate the capabilities of AI agent frameworks in various scenarios.

## Setup and Installation

### Prerequisites

It is recommended to use a Python virtual environment to manage dependencies.

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

### Install Dependencies

Install the required Python packages using `requirements.txt`:

```bash
pip install -r requirements.txt
```

### Environment Configuration

The repository uses `python-dotenv` to load environment variables from a `.env` file in the root directory.

Create a `.env` file and configure the necessary variables for your Google Cloud Project:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## Usage

```bash
python main.py --task <task_name> --framework <framework_name>
```

### Arguments

- `--task`: The agentic task to run. Supported tasks:
  - `bug_triage`
  - `fact_finder`
  - `fact_finder_real_web`
  - `financial_model_updater`
  - `itinerary_planner`
  - `coding_agent`
- `--framework`: The framework to use for the agent. Supported frameworks:
  - `adk` (Google Agent Development Kit)
  - `langgraph`

### Examples

Run the `fact_finder` task using the ADK framework:

```bash
python main.py --task fact_finder --framework adk
```

Run the `coding_agent` task using the LangGraph framework:

```bash
python main.py --task coding_agent --framework langgraph
```
