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

## Agent Deployemnt, Running and Evaluation

`coding_agent_swe_bench` has been updated for deloying and running on Vertex Agent Engine.

The agent will clone the repository specified by the datum(currently only `swebench_test_repo_v5.json` works) using github deloy key, addressing the issue, and pushing
the changes to a remote branch. The evaluator will then pull the changes and run tests against them.

Currently only ADK is supported.

Workflow:

1. **Deploy the Agent**:
   Run the deployment script. Remember to set up `.env` with `GITHUB_DEPLOY_KEY` for the repository you want the agent to work on.

   ```bash
   python coding_agent_swe_bench/adk/deploy_agent.py
   ```

   The agent ID will be in the output.

2. **Run the Agent**:
   Run the agent using the `--remote` flag and providing the agent ID:

   ```bash
   python3 main.py --task=coding_agent_swe_bench --framework=adk --remote --agent_engine_id=xxx
   ```

