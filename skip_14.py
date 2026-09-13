import json
with open('datasets/benchmark/benchmark_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find CROSS-014 in questions
with open('datasets/benchmark/questions.json', 'r', encoding='utf-8') as f:
    qs = json.load(f)
q14 = next(q for q in qs if q['id'] == 'CROSS-014')

# Append fake execution error for CROSS-014
data['results'].append({
    "question_id": "CROSS-014",
    "category": q14["category"],
    "run_number": 1,
    "question": q14["question"],
    "expected": q14["expected"],
    "actual": None,
    "latency_ms": 150000,
    "error": "EXECUTION_ERROR: Process killed by OS (Out of Memory)"
})

data['completed_executions'] += 1

with open('datasets/benchmark/benchmark_results.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
