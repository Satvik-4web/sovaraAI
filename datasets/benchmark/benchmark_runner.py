import json
import time
from main import run_sovara_task

def run_benchmark():
    with open('datasets/benchmark/questions.json') as f:
        questions = json.load(f)
        
    results = []
    
    for q in questions:
        print(f"\\nRunning Benchmark: {q['id']}")
        t0 = time.time()
        res = run_sovara_task(q['query'], q.get('files', []))
        dur = time.time() - t0
        
        # Verify conditions
        passed = False
        if q['type'] == 'rag':
            passed = len(res['citations']) > 0
        elif q['type'] == 'excel':
            passed = res['status'] == 'COMPLETED'
        elif q['type'] == 'calculation':
            passed = res['status'] == 'COMPLETED'
        elif q['type'] == 'out_of_knowledge':
            passed = res['risk']['risk_level'] == 'HIGH'
        elif q['type'] == 'cross_modal':
            passed = res['status'] == 'COMPLETED'
            
        results.append({
            'id': q['id'],
            'passed': passed,
            'latency': dur,
            'answer': res['answer'],
            'risk': res['risk']['risk_level'] if res.get('risk') else None
        })
        
    with open('datasets/benchmark/benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
        
    print("\\n=== Benchmark Complete ===")
    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['id']} ({r['latency']:.2f}s)")
        
if __name__ == '__main__':
    run_benchmark()
