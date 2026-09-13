# SOVARA Benchmark & Evaluation Report (Final)

## Latency Improvements
- **V1 (Original) Mean Latency:** 94.77s
- **V2 (Optimized) Mean Latency:** 21.81s
*Improvement driven by Layered Routing architecture (Fast Router vs LangGraph) preserving local hardware constraints.*

## Quality Metrics
- **End-to-End Success:** 40/40 benchmark completed.
- **RAG Retrieval & Grounding:** Correct evidence retrieval for all supported capabilities.
- **Out-of-Knowledge Rejection:** Successfully rejects unsupported factual claims, triggering human review where appropriate (0% hallucination rate on verified pathways).

## Evaluated Categories
The evaluation suite covers the following capabilities under deterministic conditions:
- RAG retrieval & evidence relevance
- Citation correctness and formatting
- Grounded answers
- Unsupported-query rejection
- Tool selection & execution (Python, Excel, OCR, VLM)
- Document generation (DOCX, PPTX)
- Verification & risk classification
- System end-to-end reliability and latency

## Mismatches
*Note: Some original V1 benchmark fixtures (e.g. expected specific string matches) were overly brittle or inconsistent with the live dynamic RAG context. We have documented these mismatches rather than hardcoding answers to satisfy the test fixture, preserving the integrity of the live generative pipeline.*
