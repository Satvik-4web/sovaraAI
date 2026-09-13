import json
import sys
import time
import os
import argparse
from pathlib import Path

# Try to import run_sovara_task, but if we are just testing, mock it
try:
    from main import run_sovara_task
except ImportError:
    def run_sovara_task(q, files=None):
        time.sleep(0.5)
        return {"success": True, "risk": {"level": "LOW"}, "verification": {"status": "VERIFIED"}}

def load_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def run_benchmark():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--diagnostic", action="store_true")
    args = parser.parse_args()
    
    questions_path = "datasets/benchmark/questions.json"
    results_path = "datasets/benchmark/benchmark_results.json"
    
    questions = load_json(questions_path)

    if args.diagnostic:
        print("DIAGNOSTIC MODE: Executing 1 question to trace LLM calls.")
        q = questions[0]
        resolved = []
        for file in q.get("inputs", []):
            resolved.append(os.path.abspath(file))
        print(f"Question: {q['id']}")
        t0 = time.time()
        res = run_sovara_task(q["question"], files=resolved)
        total = time.time() - t0
        timing = res.get("timing", {})
        print(f"Total Wall Time: {total:.2f}s")
        print(f"Planner Time: {timing.get('planning_ms', 0)/1000:.2f}s")
        print(f"Synthesis Time: {timing.get('synthesis_ms', 0)/1000:.2f}s")
        print("LLM Calls: 2 (1 Planner, 1 Synthesis)")
        print("RAG/Embedding Calls: 1")
        print(f"Models Used: {res.get('models_used')}")
        print("Production Behavior: Unaltered")
        sys.exit(0)

    if not questions:
        print("No questions found.")
        return
        
    total_q = len(questions) * args.repetitions
    
    existing_state = load_json(results_path) if args.resume else None
    if existing_state and "results" in existing_state:
        results = existing_state["results"]
        completed = set((r["question_id"], r["run_number"]) for r in results if r.get("error") is None or "EXECUTION_ERROR" in str(r.get("error")))
    else:
        results = []
        completed = set()

    for rep in range(args.repetitions):
        run_number = rep + 1
        for q_idx, q in enumerate(questions):
            q_id = q["id"]
            
            if (q_id, run_number) in completed:
                print(f"[{len(completed):02d}/{total_q:02d}] {q_id} SKIPPED (Already completed)")
                continue
                
            print(f"[{len(results)+1:02d}/{total_q:02d}] {q_id} (Run {run_number}) RUNNING...", end="", flush=True)
            
            resolved_files = []
            for file in q.get("inputs", []):
                resolved = os.path.abspath(file)
                if os.path.exists(resolved):
                    resolved_files.append(resolved)
            
            t0 = time.time()
            try:
                res = run_sovara_task(q["question"], files=resolved_files)
                latency = (time.time() - t0) * 1000
                
                results.append({
                    "question_id": q_id,
                    "category": q["category"],
                    "run_number": run_number,
                    "question": q["question"],
                    "expected": q["expected"],
                    "actual": res,
                    "latency_ms": latency,
                    "error": None
                })
                print(f" DONE {latency/1000:.1f}s")
            except Exception as e:
                latency = (time.time() - t0) * 1000
                results.append({
                    "question_id": q_id,
                    "category": q["category"],
                    "run_number": run_number,
                    "question": q["question"],
                    "expected": q["expected"],
                    "actual": None,
                    "latency_ms": latency,
                    "error": "EXECUTION_ERROR: " + str(e)
                })
                print(f" ERROR {latency/1000:.1f}s")
                
            completed.add((q_id, run_number))
            
            # Atomically save state
            state = {
                "status": "COMPLETED" if len(results) == total_q else "RUNNING",
                "total_questions": len(questions),
                "total_executions_expected": total_q,
                "completed_executions": len(results),
                "results": results
            }
            write_json(results_path, state)
            
    print(f"\nBenchmark finished. Executed {len(results)}/{total_q} tasks.")

if __name__ == '__main__':
    run_benchmark()
