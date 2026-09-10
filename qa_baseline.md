# SOVARA AI Core Baseline

## Baseline Command
python main.py --demo

## Timing Metrics (CPU Bound)
- **planning_ms**: 62054.37 ms
- **rag_ms**: 5832.62 ms
- **tool_ms**: 0.00 ms (Excel execution is bundled into executor timing but analysis is extremely fast)
- **synthesis_ms**: 122067.44 ms
- **verification_ms**: 1.61 ms
- **risk_ms**: 0.00 ms
- **total_ms**: 408083.76 ms

## Final Result
**Status**: COMPLETED
**Risk**: HIGH
**Human Review**: True
**Answer**: Synthesis error: HTTPConnectionPool(host='localhost', port=11434): Read timed out. (read timeout=120)

## Generated Files
- outputs/<uuid>/Approval_Note.docx (Generated correctly by the deterministic system despite synthesis timeout).

## LLM Calls
1. **Planner**: qwen3:4b
2. **Vision**: qwen2.5vl:3b
3. **Synthesis**: qwen3:4b (Wait, it selected gemma3:4b in the previous test log. But it's hardcoded to qwen3:4b in executor.py. This confirms 1B is needed.)
