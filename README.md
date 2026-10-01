# SOVARA

### Sovereign Industrial Intelligence

Local-first conversational agentic AI for confidential industrial knowledge work.

SOVARA combines local language models, retrieval, multimodal document understanding, deterministic tools, and rigorous verification into a controlled AI workspace.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)
![Ollama](https://img.shields.io/badge/Ollama-Local_Inference-white?style=flat-square)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-C52243?style=flat-square)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange?style=flat-square)

---

## Table of Contents
- [Why SOVARA?](#why-sovara)
- [What SOVARA Does](#what-sovara-does)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Local-First & Security](#local-first--security)
- [Example Workflow](#example-workflow)
- [Evaluation](#evaluation)
- [Performance Engineering](#performance-engineering)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Local Models](#local-models)
- [API Overview](#api-overview)
- [Current Limitations](#current-limitations)
- [Roadmap](#roadmap)
- [Origin](#origin)
- [Engineering Principles](#engineering-principles)
- [License](#license)

---

## Why SOVARA?

Industrial environments can work with:
- confidential manuals
- maintenance procedures
- inspection reports
- engineering drawings
- spreadsheets
- internal correspondence
- operational data

Sending sensitive material to external AI APIs may conflict with organizational privacy, security or deployment requirements.

SOVARA explores a different architecture:

```text
CONFIDENTIAL DATA
        |
        v
LOCAL AI WORKBENCH
        |
        v
RAG / VISION / OCR / TOOLS
        |
        v
EVIDENCE
        |
        v
VERIFICATION
        |
        v
CONTROLLED OUTPUT
```

SOVARA is designed around local execution and controlled data flow.
*Note: Local software execution does not inherently prove a physical network air-gap. Physical air-gapping is a deployment/network property.*

---

## What SOVARA Does

This repository implements the following core capabilities:

- **Conversational interaction:** Maintain session context with a local LLM.
- **Capability-based routing:** Bypass deep agentic orchestration for simple queries.
- **RAG & Qdrant retrieval:** Semantic search over local documents using `nomic-embed-text`.
- **Multimodal document analysis:** Extract information from P&IDs and scanned PDFs using Qwen2.5-VL and EasyOCR.
- **Excel analysis & Python execution:** Deterministic tools for calculating structured measurements.
- **Document generation:** Output findings as DOCX/Markdown reports.
- **Evidence extraction & citations:** Trace claims back to retrieved source chunks.
- **Verification & Risk assessment:** Flag unsupported claims and escalate to human review.
- **Agentic orchestration:** Stateful workflow execution using LangGraph.

SOVARA acts as controlled AI assistance and decision support, not an autonomous safety-critical controller.

---

## Architecture

```text
USER
  |
  v
CONVERSATIONAL CORE
  |
  v
FAST ROUTER
  |
  +----------------+----------------+----------------+
  |                |                |
  v                v                v
 RAG             VLM/OCR          TOOLS
 Qdrant          Documents        Python/Excel
  |                |                |
  +----------------+----------------+
                   |
                   v
                EVIDENCE
                   |
                   v
               SYNTHESIS
                   |
                   v
              VERIFICATION
                   |
                   v
            RISK / HUMAN REVIEW
                   |
                   v
              FINAL ANSWER
```

### Conversational Core
Handles natural-language interaction, session context, follow-up questions, and file-aware context.
*Important distinction: Conversation history provides context. It should not automatically be treated as authoritative industrial evidence.*

### Fast Router
Agentic planning is computationally expensive. Simple requests should not always trigger the full agentic pipeline. The Fast Router dynamically evaluates incoming queries and directs them to either direct RAG, multimodal analysis, calculation tools, or full agentic orchestration, reducing latency for simple interactions.

### Agentic Orchestration
Uses LangGraph for stateful execution of complex workflows:
`UNDERSTAND -> PLAN -> SELECT CAPABILITY -> EXECUTE -> GATHER RESULTS -> SYNTHESIZE -> VERIFY -> ASSESS RISK`

### RAG
Transforms static manuals into queryable vector spaces:
`DOCUMENT -> LOADER -> CHUNKING -> EMBEDDING -> QDRANT -> RETRIEVAL -> GROUNDED RESPONSE`
This allows organizational knowledge to remain local and updatable without model retraining. Responses can reference source evidence, and retrieval can be controlled.

### Multimodal Intelligence
Utilizes a local VLM (Qwen2.5-VL) and OCR (EasyOCR) to interpret engineering drawings (P&IDs) and parse scanned PDFs.

### Tools
Provides deterministic capabilities (Python execution, Excel parsing, document generation). Deterministic tools are useful for numerical/data operations where programmatic calculations are safer than LLM predictions.

### Verification and Risk
Checks final synthesis for evidence support, citation coverage, and consistency checking. Detects insufficient-evidence situations, classifies risk, and escalates to human review.

---

## Technology Stack

| Layer | Technology | Purpose |
|------|------------|---------|
| Local Reasoning | Qwen3:4B | Local reasoning / tool calling |
| Vision | Qwen2.5-VL:3B | Image/document understanding |
| OCR | EasyOCR + PyTorch | Local text extraction |
| Embeddings | nomic-embed-text | Vector representations |
| Vector Database | Qdrant | Local retrieval |
| Orchestration | LangGraph | Stateful agent execution |
| Backend | Python / FastAPI | Local services |
| Frontend | React / TypeScript / Vite | Workbench UI |

---

## Local-First & Security

SOVARA is designed around local execution to protect confidential industrial data. 

Security mechanisms implemented:
- local model inference
- local vector database
- local OCR and VLM processing
- local document processing
- controlled tool execution
- Docker execution / sandboxing
- evidence traceability

*Note: SOVARA provides local software execution. A physical network air-gap is a deployment/network property and cannot be proven merely because the software uses localhost.*

---

## Example Workflow

**Scenario:** 
*"Analyze the vibration condition of P-101 using the inspection report, maintenance SOP and vibration history."*

1. User submits the request.
2. Conversational layer preserves context.
3. Fast Router identifies required capabilities.
4. RAG retrieves relevant SOP/maintenance evidence.
5. Multimodal processing analyzes relevant documents/images when required.
6. Excel/Python tools analyze structured measurements.
7. Evidence is aggregated.
8. SOVARA generates a grounded response.
9. Verification checks evidence support and consistency.
10. Risk assessment determines whether human review is appropriate.
11. Final answer/document is returned.

*Positioned as decision support rather than autonomous safety-critical control.*

---

## Evaluation

A 40-task engineering evaluation was conducted to measure orchestration efficiency and system latency.

**Verified Results:**
- **40-task evaluation completed.**
- **Mean latency:** 94.77s → **21.81s** (~77% reduction)
- **Planner bypass:** **24 / 40** tasks

Capability-based routing reduced unnecessary full agentic execution.

*Current benchmark results are engineering measurements rather than production accuracy certification. Some evaluation fixtures require further alignment with evolving demo data and knowledge-base contents.*

---

## Performance Engineering

Running local AI models requires significant engineering trade-offs:
**PRIVACY + LOCAL CONTROL** vs **LATENCY + HARDWARE CONSTRAINTS**

Local inference can have higher latency than cloud inference due to limited GPU VRAM, model loading/unloading, and multimodal inference cost. SOVARA combats this primarily through capability-based routing (so simple requests avoid expensive orchestration) and relying on deterministic tools.

---

## Project Structure

```text
sovaraAI/
├── agents/              # Orchestration, planner, and chat engine
├── datasets/            # Benchmark definitions and evaluation data
├── multimodal/          # Vision and OCR processing modules
├── Rag/                 # Ingestion and retrieval logic
├── routing/             # Fast Router classification logic
├── tests/               # End-to-end tests and unit tests
├── tools/               # Deterministic tools (Python, Excel, file ops)
├── uploads/             # Ephemeral local storage for session attachments
├── verification/        # Evidence validation and risk assessment
├── api_server.py        # FastAPI backend server
├── patch_api.py         # Conversational endpoints router
└── requirements.txt     # Backend dependencies
```

*(The frontend UI is housed in a separate `sovara-ai-workbench` repository).*

---

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js (for frontend)
- Ollama daemon running

### Clone
```bash
git clone https://github.com/Satvik-4web/sovaraAI.git
cd sovaraAI
```

### Backend Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Local Model Setup
```bash
ollama pull qwen3:4b
ollama pull qwen2.5-vl
ollama pull nomic-embed-text
```

### Run Backend
```bash
python api_server.py
```
*(Server runs on port 8000 by default)*

---

## API Overview

FastAPI automatically exposes the OpenAPI schema and an interactive Swagger UI. Once the server is running, you can explore and test the endpoints at:
- **Swagger UI:** `http://localhost:8000/docs`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat/session` | POST | Initialize a new conversational session |
| `/api/chat/session/{session_id}` | GET | Retrieve session context |
| `/api/chat/message/{session_id}` | POST | Send a message (returns SSE stream) |
| `/api/chat/sessions` | GET | List all active sessions |
| `/api/tasks` | POST | Submit an asynchronous execution task |
| `/api/tasks/{task_id}/files` | POST | Upload files to a task |
| `/api/tasks/{task_id}/run` | POST | Execute a complex task |

---

## Current Limitations

### Local inference latency
Local open-weight models can be slower than cloud AI systems with large GPU infrastructure.

### Hardware constraints
Consumer GPUs can constrain model size, context, concurrency and multimodal workloads.

### Multimodal latency
Vision-language models can be significantly slower than text-only models.

### Sandbox environment
If Docker is unavailable in the Windows development environment, a local fallback may be used, but it does not provide equivalent container isolation.

### Benchmark alignment
Some benchmark fixtures are not perfectly aligned with current demo data.

---

## Roadmap

### Completed
- Capability-based routing and Planner bypass
- Multimodal extraction (VLM + OCR)
- Deterministic Python/Excel tools
- RAG integration with local Qdrant

### In Progress
- Expanding industrial evaluation datasets
- Improving table extraction

### Planned
- stronger multi-turn memory
- better retrieval/reranking
- improved P&ID understanding
- enterprise RBAC hardening
- deployment automation

---

## Origin

SOVARA was originally developed for Smart India Hackathon 2026 under industrial AI problem statement SIH26117. 

Developed for the SIH 2026 challenge; the project was not shortlisted. 

SIH was the catalyst. 
SOVARA is the project.

---

## Engineering Principles

### Local by Design
Sensitive workflows should not require external AI APIs during local execution.

### Evidence over Unsupported Generation
Industrial claims should be grounded in retrieved or tool-generated evidence.

### Deterministic Tools Where Appropriate
Use Python/Excel tools for calculations instead of asking the LLM to perform every operation.

### Route Before Orchestrating
Use the cheapest capable execution path before invoking a complex agentic workflow.

### Human Review for Uncertainty
Insufficient evidence and higher-risk outputs should be surfaced for review.

---

## License

License: Not yet specified.

