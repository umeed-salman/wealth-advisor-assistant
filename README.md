# Wealth Advisor Assistant

A multi-agent system for automated financial analysis and advisory recommendations with human-in-the-loop approval workflows. Built with LangGraph orchestration, FastAPI backend, and a Streamlit frontend client.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Multi-Agent System](#multi-agent-system)
3. [Key Decisions & Trade-offs](#key-decisions--trade-offs)
4. [Assumptions](#assumptions)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Running the Project](#running-the-project)
8. [Running Tests](#running-tests)
9. [API Reference](#api-reference)
10. [Configuration](#configuration)

---

## Architecture

### High-Level Design
<img width="1381" height="551" alt="image" src="https://github.com/user-attachments/assets/d7507342-843f-4421-ae03-e3dab32d99b7" />

---

### Component Breakdown

**Frontend (Streamlit)**
- HTTP-based client running on port 8501 (Streamlit default)
- Sends API requests to backend via httpx
- Displays analysis results and approval workflow
- Sidebar includes usage guide and status indicators
- Separate deployment from backend (independently scalable)

**Backend (FastAPI)**
- REST API on port 8000
- Orchestrator coordinates multi-agent flow via LangGraph
- Three-stage processing: data fetching → analysis → approval
- Stateless HTTP endpoints (state persisted to disk/memory)

**LangGraph StateGraph**
- **Node 1: Fetch Context** — Retrieves CRM data and enriches client profile; falls back to deterministic defaults on failure
- **Node 2: Analyze** — Computes financial metrics (cashflow, savings rate, debt-to-income, emergency fund), detects anomalies, generates LLM-driven recommendations
- **Node 3: Approval Gate** — Routes to manual approval (waits for human decision) or auto-approval (immediate completion)

**Persistence Layer**
- **RunStore**: In-memory storage for active advisory runs with full metadata
- **ArtifactStore**: Writes completed runs to `output/runs/{run_id}.json` for audit trail and long-term storage
- **MemoryStore**: Appends historical summaries to `output/memory/history.jsonl` for learning and pattern analysis

**LLM Integration (LiteLLM)**
- Provider-agnostic abstraction via LiteLLM library
- Default: Ollama with llama3.2 model (http://localhost:11434)
- Supports OpenAI-compatible endpoints by config change
- Deterministic fallback if LLM unavailable (ensures advisory continues)

---

## Multi-Agent System

This diagram illustrates the interaction between the orchestrator and the specialized agents.
<img width="875" height="651" alt="image" src="https://github.com/user-attachments/assets/03842b29-af39-4e80-85df-7957d63d3cd2" />

---

## Key Decisions & Trade-offs

- **LangGraph for Orchestration**: Chosen for its explicit state management, visualization capabilities, and support for human-in-the-loop workflows. It makes complex flows easier to debug and modify compared to less structured agent frameworks.
- **FastAPI for Backend**: High-performance, easy to learn, and provides automatic OpenAPI documentation, which is ideal for building a robust API.
- **Streamlit for Frontend**: Rapid UI development with Python. Perfect for internal tools and dashboards where speed of iteration is critical. The trade-off is less design flexibility compared to frameworks like React or Vue.
- **LiteLLM for Model Abstraction**: Decouples the application from any single LLM provider. This allows swapping models (e.g., from a local Ollama instance to OpenAI's API) with only a configuration change, enhancing flexibility and future-proofing the system.
- **Human-in-the-Loop by Default**: The `approval_mode` defaults to `manual` to ensure a human reviews the AI-generated advice before it's finalized. This is a critical safety feature in a financial context.
- **Disk-Based Persistence**: Using JSON and JSONL files for persistence is simple and requires no external database, making the project easy to run locally. The trade-off is that it's not suitable for high-concurrency production environments, where a proper database like PostgreSQL would be needed.

---

## Assumptions

- The user has Python 3.12+ and `pip` installed.
- The user has Ollama installed or has access to llm apis
- The user has access to a running LLM that is compatible with the OpenAI API standard (e.g., Ollama or the OpenAI API itself).
- The input data for clients is provided as JSON files in the `input/` directory.

---

## Project Structure

```
.
├── .env.example            # Example environment variables
├── data/                   # Default data directory
├── frontend/
│   └── streamlit_app.py    # Streamlit frontend application
├── input/                  # Input client data files
├── output/                 # Output directory for runs and memory
├── src/
│   └── wealth_advisor/     # Main application source code
│       ├── agents/         # Specialized agents (Analyzer, DataFetcher)
│       ├── api/            # FastAPI routes
│       ├── services/       # Core services (LLM, Memory, etc.)
│       ├── tools/          # Tools for agents (FinancialAnalysis, CRM)
│       ├── config.py       # Application configuration
│       ├── orchestrator.py # LangGraph orchestration logic
│       └── models.py       # Pydantic data models
├── tests/                  # Pytest tests
├── README.md               # This file
└── requirements.txt        # Python dependencies
```

---

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**: You can download it from [python.org](https://www.python.org/).
- **An LLM Provider**: This project is configured to use a local LLM with Ollama by default, but it can be configured to use any OpenAI-compatible API.

### Option 1: Using Ollama (Default)

1.  **Install Ollama**: Follow the instructions on the [Ollama website](https://ollama.ai/) to download and install it for your operating system.

2.  **Download a Model**: Once Ollama is running, open your terminal and pull a model. The default model for this project is `llama3.2`, which you can get by running:
    ```bash
    ollama pull llama3.2
    ```
    The application will automatically connect to the Ollama server running at `http://localhost:11434`.

### Option 2: Using Other LLM Providers (e.g., OpenAI)

This project uses **LiteLLM** to connect to various LLM providers. To use a different provider like OpenAI, you need to update the `.env` file.

1.  **Get an API Key**: Sign up for an account with your chosen provider (e.g., [OpenAI](https://platform.openai.com/)) and get an API key.

2.  **Update the `.env` file**:
    - Copy `.env.example` to `.env`.
    - Set the `WEALTH_ADVISOR_LLM_PROVIDER` to the name of the provider (e.g., `openai`).
    - Set the `WEALTH_ADVISOR_LLM_MODEL` to the model you want to use (e.g., `gpt-4o`).
    - Set `WEALTH_ADVISOR_LLM_API_KEY` to your API key.
    - If you are using a self-hosted or alternative endpoint, update `WEALTH_ADVISOR_LLM_API_BASE`.

    Example for OpenAI:
    ```env
    WEALTH_ADVISOR_LLM_PROVIDER="openai"
    WEALTH_ADVISOR_LLM_MODEL="gpt-4o"
    WEALTH_ADVISOR_LLM_API_KEY="your-openai-api-key"
    ```

---

## Running the Project

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-name>
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the environment:**
    - Copy `.env.example` to `.env`.
    - Modify `.env` to point to your LLM provider and set other configurations as needed. By default, it expects an Ollama server running at `http://localhost:11434`.

5.  **Run the backend server:**
    ```bash
    uvicorn src.main:app --reload
    ```
    The API will be available at `http://localhost:8000` and the documentation at `http://localhost:8000/docs`.

6.  **Run the frontend application:**
    In a separate terminal, run:
    ```bash
    streamlit run frontend/streamlit_app.py
    ```
    The Streamlit UI will be available at `http://localhost:8501`.

7. **Demo:**
   [![Demo Thumbnail](https://github.com/user-attachments/assets/474a2771-17f5-44e5-b0fb-51b60d56b928
)](https://github.com/user-attachments/assets/b68048a8-8765-46f0-82be-0f4f7cce75ce)

---

## Running Tests

This project uses `pytest` for testing. To run the test suite, follow these steps:

1.  **Ensure all dependencies are installed**, including the test-specific ones listed in `requirements.txt`.

2.  **Run pytest from the root directory**:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run the tests in the `tests/` directory.

---

## API Reference

The API is self-documented using OpenAPI. Once the backend server is running, you can access the interactive documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

Key endpoints include:
- `POST /runs/`: Start a new advisory run.
- `GET /runs/{run_id}`: Get the status and result of a run.
- `POST /runs/{run_id}/approve`: Approve a run that is pending manual approval.

---

## Configuration

Configuration is managed via environment variables and a `.env` file. See `.env.example` for all available options.

- **`WEALTH_ADVISOR_LLM_PROVIDER`**: The LLM provider to use (e.g., `ollama`, `openai`).
- **`WEALTH_ADVISOR_LLM_MODEL`**: The specific model to use (e.g., `llama3.2`).
- **`WEALTH_ADVISOR_APPROVAL_MODE`**: Set to `manual` or `auto`.
- **`WEALTH_ADVISOR_INPUT_DIR`**: Directory to read client data from.
- **`WEALTH_ADVISOR_OUTPUT_DIR`**: Directory to write run artifacts and memory to.
