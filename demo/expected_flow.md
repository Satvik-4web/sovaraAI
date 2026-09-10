# Expected Execution Flow
1. User requests analysis.
2. Planner identifies multimodal, ag, and excel capabilities.
3. Executor extracts text from PDF, parses PID image, and loads Excel data.
4. RAG retrieves relevant SOP steps.
5. Synthesis aggregates all findings into a concise note.
6. Verification bounds risk level.
7. Output generated as a .docx file.
