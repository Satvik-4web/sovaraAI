import json
import numpy as np

def score_results(results_path):
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    metrics = {
        "retrieval_accuracy": 0.0,
        "evidence_relevance": 0.0,
        "citation_correctness": 0.0,
        "grounded_answer_rate": 0.0,
        "hallucination_rate": 0.0,
        "unsupported_query_rejection": 0.0,
        "tool_selection_accuracy": 0.0,
        "tool_execution_success": 0.0,
        "calculation_accuracy": 0.0,
        "OCR_accuracy": 0.0,
        "pid_accuracy": 0.0,
        "verification_accuracy": 0.0,
        "risk_classification_accuracy": 0.0,
        "end_to_end_success": 0.0,
        "latency_ms": 0.0,
        "p95_latency": 0.0
    }
    
    total = len(results)
    if total == 0:
        return metrics
        
    passed = 0
    latencies = []
    
    rag_count = 0
    pid_count = 0
    excel_count = 0
    calc_count = 0
    safety_count = 0
    cross_count = 0
    
    rag_hits = 0
    pid_hits = 0
    excel_hits = 0
    calc_hits = 0
    safety_hits = 0
    cross_hits = 0
    
    risk_hits = 0
    verif_hits = 0
    tool_exec_hits = 0
    
    # Deterministic scoring
    for r in results:
        latencies.append(r["latency_ms"])
        
        expected = r.get("expected", {})
        cat = expected.get("category", "")
        truth = expected.get("ground_truth", "")
        req_ev = expected.get("required_evidence", [])
        exp_risk = expected.get("expected_risk", "LOW")
        exp_verif = expected.get("expected_verification", "VERIFIED")
        
        res_data = r.get("result")
        if not res_data or not isinstance(res_data, dict):
            continue
            
        success = res_data.get("success", False)
        risk = res_data.get("risk", {}).get("level", "LOW")
        verif = res_data.get("verification", {}).get("status", "VERIFIED")
        
        # Risk / Verif
        if risk == exp_risk:
            risk_hits += 1
        if verif == exp_verif:
            verif_hits += 1
            
        if success:
            tool_exec_hits += 1
            
        # Category specific logic
        # For simplicity in this demo deterministic scorer, we check if truth terms exist in outputs/events
        # or if expected behavior aligns with final state.
        is_correct = False
        
        if cat == "rag":
            rag_count += 1
            if success and all(term.lower() in str(res_data).lower() for term in req_ev):
                rag_hits += 1
                is_correct = True
        elif cat == "pid":
            pid_count += 1
            if success and all(term.lower() in str(res_data).lower() for term in req_ev):
                pid_hits += 1
                is_correct = True
        elif cat == "excel":
            excel_count += 1
            if success and all(term.lower() in str(res_data).lower() for term in req_ev):
                excel_hits += 1
                is_correct = True
        elif cat == "calc":
            calc_count += 1
            if success:
                calc_hits += 1
                is_correct = True
        elif cat == "safety":
            safety_count += 1
            if risk == "HIGH" and verif == "NEEDS_REVIEW":
                safety_hits += 1
                is_correct = True
        elif cat == "cross" or cat == "contradiction":
            cross_count += 1
            if risk == exp_risk:
                cross_hits += 1
                is_correct = True
                
        if is_correct:
            passed += 1

    metrics["retrieval_accuracy"] = rag_hits / max(1, rag_count)
    metrics["pid_accuracy"] = pid_hits / max(1, pid_count)
    metrics["OCR_accuracy"] = pid_hits / max(1, pid_count) # proxy
    metrics["tool_execution_success"] = excel_hits / max(1, excel_count)
    metrics["calculation_accuracy"] = calc_hits / max(1, calc_count)
    metrics["unsupported_query_rejection"] = safety_hits / max(1, safety_count)
    metrics["risk_classification_accuracy"] = risk_hits / total
    metrics["verification_accuracy"] = verif_hits / total
    metrics["end_to_end_success"] = passed / total
    metrics["hallucination_rate"] = 1.0 - metrics["end_to_end_success"]
    
    metrics["latency_ms"] = float(np.mean(latencies)) if latencies else 0.0
    metrics["p95_latency"] = float(np.percentile(latencies, 95)) if latencies else 0.0
    
    summary = {
        "total_tests": total,
        "passed": passed,
        "failed": total - passed,
        "metrics": metrics
    }
    
    # Write summary
    with open(results_path.replace(".json", "_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    score_results("datasets/benchmark/benchmark_results.json")
