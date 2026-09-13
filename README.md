# SOVARA: Industrial AI Workbench

SOVARA is an intelligent, air-gapped Industrial AI assistant designed for multimodal document analysis, RAG, and execution.

## Local-Only Architecture
SOVARA is 100% local. It runs locally without telemetry, external API calls, or cloud dependencies. Physical network isolation must be enforced by deployment infrastructure.
- **LLM:** Qwen3:4B (via local Ollama)
- **VLM:** Qwen2.5-VL (via local Ollama)
- **Embeddings:** nomic-embed-text
- **Vector DB:** Qdrant (local)
- **OCR:** EasyOCR + PyTorch

## Setup Instructions

1. **Python Version:** Python 3.10+
2. **Virtual Environment:** 
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. **Required Packages:** `pip install -r requirements.txt`
4. **Ollama:** Install from ollama.com. Ensure the daemon is running.
5. **Required Models:** `ollama pull qwen3:4b`, `ollama pull qwen2.5-vl`, `ollama pull nomic-embed-text`
6. **Qdrant Setup:** Qdrant runs entirely locally using file-based storage.
7. **Knowledge Base Ingestion:** `python -m Rag.ingest`
8. **Backend Startup:** `python api_server.py`
9. **Frontend Startup:** In `sovara-ai-workbench`, run `npm install` then `npm run dev`.

## Running the Hero Workflow
Use the assets in the `demo/` folder (e.g. `pump_inspection.xlsx`, `inspection_report.pdf`, `pump_pid.png`).
Upload them and ask: "Analyze the uploaded pump inspection using the P&ID, inspection report, maintenance SOP and spreadsheet. Identify abnormal conditions, calculate the relevant vibration statistic, compare the findings with the SOP, and prepare an approval note."

## Security Considerations
**DEVELOPMENT:** Local fallback may be used for Python sandbox execution.
**PRODUCTION:** Docker/container isolation must be used for sandbox execution to guarantee secure code execution.
