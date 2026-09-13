import json
import numpy as np
import os

def check_evidence(expected_ev, actual):
    if not expected_ev: return True
    
    rag_evs = actual.get("evidence", [])
    tool_evs = actual.get("deliverables", [])
    
    for req in expected_ev:
        req_source = req.get("source")
        found = False
        
        # If the benchmark author put 'Qdrant' as the source, accept any valid RAG evidence
        if req_source == "Qdrant" and len(rag_evs) > 0:
            found = True
            continue
            
        # check RAG
        for rev in rag_evs:
            if req_source == rev.get("source"):
                found = True
                break
        if found: continue
        
        # check Tools
        for tev in tool_evs:
            t_res = tev.get("result", {}).get("result", {})
            if isinstance(t_res, dict):
                if t_res.get("file_name") == req_source or t_res.get("filename") == req_source:
                    found = True
                    break
        if not found: return False
        
    return True

def score_results():
    results_file = "datasets/benchmark/benchmark_results.json"
    if not os.path.exists(results_file): return
    with open(results_file, "r", encoding="utf-8") as f:
        state = json.load(f)
        
    results = state.get("results", [])
    detailed = []
    
    passes = 0
    partials = 0
    fails = 0
    grounded_count = 0
    hallucination_count = 0
    latencies = [r.get("latency_ms", 0) for r in results]
    
    for r in results:
        expected = r.get("expected", {})
        actual = r.get("actual", {}) or {}
        
        if r.get("error") and "EXECUTION_ERROR" in r.get("error"):
            fails += 1
            detailed.append({"question_id": r["question_id"], "status": "FAIL", "score": 0.0, "failure_codes": ["PIPELINE_ERROR"]})
            continue
            
        req_facts = expected.get("required_facts", [])
        forbid_claims = expected.get("forbidden_claims", [])
        req_ev = expected.get("required_evidence", [])
        req_tools = expected.get("required_tools", [])
        exp_risk = expected.get("expected_risk", "LOW")
        
        ans = str(actual.get("answer", "")).lower()
        
        facts_matched = [f for f in req_facts if f.lower() in ans]
        claims_found = [f for f in forbid_claims if f.lower() in ans]
        
        actual_risk = actual.get("risk", {}).get("level", "LOW") if actual.get("risk") else "UNKNOWN"
        risk_match = actual_risk == exp_risk
        
        evidence_match = check_evidence(req_ev, actual)
        
        # Check tools - allow synonym mapping between required 'rag' and actual 'search' action
        actual_tools = [step.get("tool") for step in actual.get("deliverables", [])] + [step.get("action") for step in actual.get("plan", [])]
        actual_capabilities = [step.get("required_capability") for step in actual.get("plan", [])]
        
        all_actual_tools_and_caps = set(actual_tools + actual_capabilities)
        tools_match = all((rt in all_actual_tools_and_caps) or (rt == "rag" and "search" in all_actual_tools_and_caps) for rt in req_tools) if req_tools else True
        
        score = 0
        r_status = "FAIL"
        failure_codes = []
        
        fact_ratio = len(facts_matched) / max(1, len(req_facts)) if req_facts else 1.0
        
        if not evidence_match: failure_codes.append("MISSING_EVIDENCE")
        if not tools_match: failure_codes.append("MISSING_TOOL")
        if fact_ratio < 1.0: failure_codes.append("MISSING_FACTS")
        if claims_found: failure_codes.append("HALLUCINATION")
        if not risk_match: failure_codes.append("WRONG_RISK")
        
        if fact_ratio == 1.0 and len(claims_found) == 0 and risk_match and evidence_match and tools_match:
            r_status = "PASS"
            passes += 1
            score = 1.0
            grounded_count += 1
        elif fact_ratio > 0.0 or risk_match or evidence_match:
            r_status = "PARTIAL"
            partials += 1
            score = 0.5
            hallucination_count += 1
        else:
            r_status = "FAIL"
            fails += 1
            hallucination_count += 1
            
        detailed.append({
            "question_id": r["question_id"],
            "category": r.get("category", "unknown"),
            "run_number": r["run_number"],
            "status": r_status,
            "score": score,
            "failure_codes": failure_codes,
            "latency_ms": r.get("latency_ms", 0)
        })
        
    total = max(1, len(results))
    summary = {
        "status": state.get("status"),
        "total_questions": len(results),
        "overall_pass_rate": passes / total,
        "overall_partial_rate": partials / total,
        "overall_fail_rate": fails / total,
        "grounded_answer_rate": grounded_count / total,
        "hallucination_rate": hallucination_count / total,
        "mean_latency_ms": float(np.mean(latencies)) if latencies else 0,
        "p95_latency_ms": float(np.percentile(latencies, 95)) if latencies else 0,
        "quality_gates": {
            "grounding": (grounded_count / total) >= 0.95,
            "hallucination": (hallucination_count / total) <= 0.02,
            "end_to_end": (passes / total) >= 0.90
        }
    }
    summary["quality_gate_status"] = "PASS" if all(summary["quality_gates"].values()) else "FAIL"
    
    with open("datasets/benchmark/benchmark_results_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open("datasets/benchmark/benchmark_detailed_results.json", "w", encoding="utf-8") as f:
        json.dump(detailed, f, indent=2)

if __name__ == '__main__':
    score_results()
