import json
import time
import os
from main import run_sovara_task
import random

def run_benchmark():
    questions_path = "datasets/benchmark/questions.json"
    results_path = "datasets/benchmark/benchmark_results.json"
    
    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
        
    results = []
    
    # We will sample 10 representative queries to ensure execution completes in a reasonable time
    # We pick 2 RAG, 2 PID, 2 Excel, 1 Calc, 2 Safety, 1 Cross
    sampled = []
    for q in questions:
        c = q["category"]
        count = sum(1 for x in sampled if x["category"] == c)
        if c == "rag" and count < 2: sampled.append(q)
        elif c == "pid" and count < 2: sampled.append(q)
        elif c == "excel" and count < 2: sampled.append(q)
        elif c == "calc" and count < 1: sampled.append(q)
        elif c == "safety" and count < 2: sampled.append(q)
        elif c == "cross" and count < 1: sampled.append(q)
    
    for idx, q in enumerate(sampled):
        print(f"Running [{idx+1}/{len(sampled)}]: {q['id']}")
        
        resolved_files = []
        for file in q.get("input_files", []):
            resolved = os.path.abspath(file)
            if os.path.exists(resolved):
                resolved_files.append(resolved)
        
        t0 = time.time()
        try:
            res = run_sovara_task(q["question"], files=resolved_files)
            latency = (time.time() - t0) * 1000
            
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected": q,
                "result": res,
                "latency_ms": latency,
                "error": None
            })
        except Exception as e:
            latency = (time.time() - t0) * 1000
            results.append({
                "id": q["id"],
                "question": q["question"],
                "expected": q,
                "result": None,
                "latency_ms": latency,
                "error": str(e)
            })
            
        with open(results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
            
    print(f"Finished running {len(sampled)} benchmarks.")

if __name__ == '__main__':
    run_benchmark()
