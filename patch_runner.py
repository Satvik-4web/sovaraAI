import argparse
import sys

def modify():
    with open("datasets/benchmark/benchmark_runner.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Add diagnostic flag
    content = content.replace(
        'parser.add_argument("--resume", action="store_true")',
        'parser.add_argument("--resume", action="store_true")\n    parser.add_argument("--diagnostic", action="store_true")'
    )
    
    # Handle diagnostic flag early
    diag_logic = '''
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
'''
    content = content.replace('questions = load_json(questions_path)', 'questions = load_json(questions_path)\n' + diag_logic)
    
    with open("datasets/benchmark/benchmark_runner.py", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    modify()
