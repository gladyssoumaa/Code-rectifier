# Code-rectifier
An autonomous agentic AI assistant that monitors my local development directory, detects script failures/errors in real-time, diagnoses errors using external documentation, and self-corrects the code through an iterative execution loop. 

This demonstrates the practical application of **Agentic AI architecture**, **event-driven file monitoring**, and **closed-loop self-correction systems**.

## Core Capabilities
* **Real-Time Directory Monitoring:** Tracks file changes and auto-triggers test suites upon file saves.
* **Algorithmic Self-Healing Loop:** Implements a strict **Reasoning + Action (ReAct)** cycle to diagnose, patch, and re-test broken scripts without human intervention.
* **Dynamic Tool Integration:** Empowers the LLM with local system access (file read/write) and global knowledge access (Web/StackOverflow search APIs).
* **Token Guardrails:** Enforces deterministic iteration limits to prevent infinite runtime loops and control API expenditures.

## Architecture & Workflow

The agent operates as a continuous finite state machine managed by LangGraph:
1. **Trigger:** The `watchdog` module detects a file save and fires a subprocess command running the local test suite.
2. **Ingestion:** If the script crashes, the stdout/stderr stack trace is parsed and injected into the agent's context window.
3. **Reasoning:** The LLM analyzes the codebase alongside the stack trace. If required, it invokes tools to search online documentation or StackOverflow.
4. **Action:** The agent writes a calculated patch directly back to the local file.
5. **Validation:** The loop reverts to Step 1. The assistant repeats this up to a hard stop threshold of 5 attempts before safety-aborting.

## Tech Stack & Dependencies

* **Orchestration Framework:** `LangGraph` (State management & cyclical agent loops)
* **File System Event Handler:** `Watchdog` (Asynchronous local directory observation)
* **Core Brain:** `OpenAI GPT-4o` / `Anthropic Claude 3.5 Sonnet` (Function calling & tool execution)
* **Runtime Isolation:** Python `subprocess` (Environment execution & exit-code capture)
* **Memory & State:** `LangGraph Memory Saver` (In-memory checkpointing for debugging histories)

## Quick Start & Installation

### 1. Clone the Repository & Install Dependencies
```bash
git clone https://github.com
cd folder
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY= my_api_key
TAVILY_API_KEY= my_search_api_key
TARGET_WATCH_DIR= my_local_folder
```

### 3. Run the Agent
```bash
python main.py
```
*Add a broken Python script into my monitored directory, save it, and watch the terminal logs as the agent detects, searches, rewrites, and resolves the bug automatically.*

---
