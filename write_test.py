import json
with open("datasets/benchmark/benchmark_results.json", "w") as f:
    json.dump({
        "status": "RUNNING",
        "total_questions": 40,
        "total_executions_expected": 40,
        "completed_executions": 2,
        "results": [{"question_id": "q1", "run_number": 1}, {"question_id": "q2", "run_number": 1}]
    }, f)
