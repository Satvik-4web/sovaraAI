# SOVARA
### Sovereign Industrial Intelligence

*Local-first conversational agentic AI for confidential industrial knowledge work.*

SOVARA combines local language models, retrieval, multimodal document understanding, deterministic tools, and rigorous verification into a single, controlled AI workspace. It is designed to orchestrate complex tasks over confidential engineering and operational data without relying on external cloud APIs.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local_Inference-white?style=flat-square)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-C52243?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange?style=flat-square)

---

## Why SOVARA?

Industrial environments often work with:
- Confidential manuals and internal procedures
- Inspection reports
- Engineering drawings (P&IDs)
- Maintenance records
- Spreadsheets and telemetry data

Sending such information to external AI APIs may conflict with organizational privacy, security, or strict deployment requirements. SOVARA explores a different architecture by keeping all execution strictly local.

```text
CONFIDENTIAL DATA
        ↓
LOCAL AI WORKBENCH
        ↓
RAG / VISION / OCR / TOOLS
        ↓
EVIDENCE
        ↓
VERIFICATION
        ↓
CONTROLLED OUTPUT
```

---

## What SOVARA Actually Does

This repository implements the following core capabilities:

- **Conversational interaction:** Maintain session context with a local LLM.
- **Capability-based routing:** Dynamically route simple queries around heavy agentic orchestration.
- **RAG & Vector Retrieval:** Local embeddings using `nomic-embed-text` and local vector storage via Qdrant.
- **Multimodal Document Analysis:** Extract information from P&IDs and scanned documents using Qwen2.5-VL and EasyOCR.
- **Data Analysis Tools:** Execute Python code and parse Excel/CSV files locally.
- **Document Generation:** Output verified reports as DOCX/Markdown.
- **Evidence & Citations:** Trace every claim back to the retrieved source chunk or tool execution.
- **Verification & Risk Assessment:** Automatically validate answers against retrieved evidence and flag high-risk or unsupported claims for human review.
- **Agentic Orchestration:** Coordinate complex tasks using LangGraph stateful execution.

---

## Architecture Workflow

```text
USER REQUEST
 ↓
CONVERSATIONAL CORE
 ↓
FAST ROUTER
 ↓
 ┌──────────────┬──────────────┬──────────────┐
 │ RAG          │ VLM / OCR    │ TOOLS        │
 │ Qdrant       │ Documents    │ Python/Excel │
 └──────────────┴──────────────┴──────────────┘
 ↓
EVIDENCE
 ↓
SYNTHESIS
 ↓
VERIFICATION
 ↓
RISK / HUMAN REVIEW
 ↓
FINAL ANSWER
```

1. **Conversational Core:** Manages the user session, conversation history, and handles file attachments.
2. **Fast Router:** Analyzes the request intent to route it either to a direct, fast response path or a deep agentic orchestration path.
3. **Execution Layer:** Dispatches work to RAG, Multimodal/Vision components, or local deterministic tools.
4. **Synthesis & Verification:** Aggregates findings and ensures the generated output is strictly supported by the gathered evidence.
5. **Risk Assessment:** Checks for safety thresholds, missing evidence, or sensitive operations, escalating to a Human-in-the-Loop (HITL) review if necessary.

---

## Architecture Deep Dive

### Conversational Layer
Handles multi-turn conversational context, tracks attached files, and manages session state.

### Fast Router
Agentic planning is computationally expensive. The Fast Router evaluates incoming queries and bypasses the heavy Planner Agent for simple questions, significantly reducing latency for trivial interactions.

### Agentic Orchestration
Implemented using LangGraph, the Planner Agent breaks down complex requests into a Directed Acyclic Graph (DAG) of sub-tasks. It selects the appropriate tools and coordinates the execution steps.

### RAG (Retrieval-Augmented Generation)
- **Loading & Chunking:** Processes uploaded text and PDFs.
- **Embeddings:** Generates embeddings locally using `nomic-embed-text`.
- **Qdrant:** Stores vectors in a local, file-based Qdrant instance.
- **Retrieval:** Performs semantic search to ground the LLM's responses.

### Multimodal Layer
Utilizes **Qwen2.5-VL** alongside **EasyOCR** (PyTorch) to interpret engineering drawings (e.g., P&IDs), detect text in scanned PDFs, and analyze visual evidence.

### Tools
- **Python Executor:** Executes generated Python code for data analysis.
- **Excel/CSV Analyzer:** Reads and extracts tabular data using `pandas` and `openpyxl`.
- **Document Generators:** Creates structured reports (DOCX, Markdown).
- **File Operations:** Manages reading and saving files locally.

### Verification & Risk
All generated answers pass through a deterministic and LLM-based verification engine. Claims are checked against the retrieved evidence. If a claim lacks support or violates physical constraints/safety protocols, it is flagged, and the risk module recommends a human review.

---

## Model Stack

| Component | Model/Technology | Purpose |
|---|---|---|
| **Reasoning / Planner** | Qwen3:4B (via Ollama) | Orchestration, intent routing, and final synthesis |
| **Vision** | Qwen2.5-VL (via Ollama) | P&ID analysis, image understanding |
| **OCR** | EasyOCR + PyTorch | Extracting text from scans and diagrams |
| **Embeddings** | nomic-embed-text | Local vector embeddings for RAG |
| **Vector DB** | Qdrant | Local semantic search |
| **Orchestration** | LangGraph | Stateful multi-agent execution |

---

## Local-First & Security

SOVARA is designed around local-first execution to protect confidential industrial data. 

- **Local Inference:** All LLM, VLM, and Embedding models run entirely on local hardware via Ollama. No external API calls are made.
- **Local Storage:** Documents and vectors are stored locally (Qdrant file-based storage).
- **Controlled Tool Execution:** Tools operate within restricted paths.
- **Sandbox Environment:** The Python execution tool supports running within a local Docker container for isolation.

**Note on Security:** 
While SOVARA's software architecture prevents telemetry and external API calls (zero-egress by design), a true physical air-gap is a deployment and network infrastructure property. SOVARA provides the *software capability* to run in such an environment, but physical security guarantees require appropriate hardware deployment.

---

## Example Workflow

**Scenario:** 
*"Analyze the vibration condition of P-101 using the inspection report, maintenance SOP and vibration history."*

1. **User Request:** Uploads `pump_inspection.xlsx`, `inspection_report.pdf`, and a P&ID diagram.
2. **Router:** Detects a complex multi-file task and engages the Planner Agent.
3. **RAG Retrieval:** Searches the Maintenance SOP for standard operating limits.
4. **Multimodal Analysis:** Analyzes the P&ID to understand the pump's system context.
5. **Excel Analysis:** Executes local Python/Pandas to extract vibration statistics from the spreadsheet.
6. **Evidence Aggregation:** Collects standard limits, system context, and actual vibration data.
7. **Synthesis & Verification:** Drafts the analysis and verifies that the reported anomaly is grounded in the retrieved Excel data.
8. **Risk Assessment:** Flags the abnormal vibration condition and marks the response for engineer review.
9. **Final Output:** Presents the verified finding with citations to the user.

---

## Benchmark & Evaluation

A 40-task engineering evaluation was conducted to measure orchestration efficiency and system latency.

**Verified Results:**
- **40-task evaluation completed.**
- **Mean latency reduction:** 94.77s → **21.81s** (~77% reduction)
- **Planner bypass:** **24 / 40** tasks successfully bypassed the heavy orchestration layer via capability-based routing.

*Note: Current evaluation includes fixture-alignment limitations and is intended as an engineering benchmark to track routing efficiency rather than a production accuracy certification.*

---

## Performance Engineering

Running local AI models requires significant engineering trade-offs between privacy and performance. Latency can be high due to:
- Constrained GPU memory requiring frequent model loading/unloading.
- Splitting workloads between CPU and GPU.
- Sequential execution of multiple specialized models (Reasoning → Vision → Embedding).

SOVARA combats this primarily through **Fast Routing**—preventing simple questions from triggering the full LangGraph orchestration—and relying on **deterministic tools** (like Python/Excel parsing) instead of LLMs wherever possible.

---

## Project Structure

```text
sovaraAI/
├── agents/              # Core LangGraph orchestration, planner, and chat engine
├── datasets/            # Benchmark definitions, scoring scripts, and evaluation data
├── multimodal/          # Vision and OCR modules (Qwen2.5-VL, EasyOCR)
├── Rag/                 # RAG implementation (Chunking, embeddings, Qdrant integration)
├── routing/             # Fast Router logic for intent classification
├── tests/               # End-to-end tests, streaming tests, and unit tests
├── tools/               # Local tool execution (Python, Excel, Document generation, Sandbox)
├── uploads/             # Ephemeral local storage for session attachments
├── verification/        # Evidence validation and risk assessment logic
├── api_server.py        # FastAPI backend server
├── main.py              # CLI/Entrypoint orchestration
└── requirements.txt     # Python dependencies
```

*(The frontend UI is housed in a separate `sovara-ai-workbench` repository built with React, TypeScript, and TailwindCSS).*

---

## Setup Instructions

1. **Prerequisites:** Python 3.10+
2. **Environment:** 
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Ollama:** Install from [ollama.com](https://ollama.com). Ensure the daemon is running.
4. **Models:** 
   ```bash
   ollama pull qwen3:4b
   ollama pull qwen2.5-vl
   ollama pull nomic-embed-text
   ```
5. **Knowledge Base:** Ingest documents using `python -m Rag.ingest`
6. **Run Backend:** `python api_server.py` (runs on port 8000 by default)

---

## SIH Context

SOVARA was conceptualized and developed as a robust technical solution for strict industrial use cases where data privacy, confident decision-making, and verification are paramount. It demonstrates how autonomous agentic patterns can be securely deployed inside enterprise firewalls.
