import json
import subprocess
import os

def write_fixture(data):
    with open("datasets/benchmark/benchmark_results.json", "w") as f:
        json.dump(data, f)

def run_score():
    res = subprocess.run(["python", "datasets/benchmark/scoring.py"], capture_output=True, text=True)
    return res.stdout.strip()

print("Testing A: 0/40")
write_fixture({
    "status": "RUNNING",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 0,
    "results": []
})
print(run_score())

print("\nTesting B: 20/40")
write_fixture({
    "status": "RUNNING",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 20,
    "results": [{"question_id": f"q{i}", "run_number": 1} for i in range(20)]
})
print(run_score())

print("\nTesting C: 40/40")
write_fixture({
    "status": "COMPLETED",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 40,
    "results": [{"question_id": f"q{i}", "run_number": 1, "expected": {}, "actual": {"success": True, "risk": {"level": "LOW"}}, "latency_ms": 100} for i in range(40)]
})
print(run_score())

print("\nTesting D: One execution error")
results = [{"question_id": f"q{i}", "run_number": 1, "expected": {}, "actual": {"success": True}, "latency_ms": 100} for i in range(39)]
results.append({"question_id": "q39", "run_number": 1, "error": "EXECUTION_ERROR: pipeline failure", "latency_ms": 100})
write_fixture({
    "status": "COMPLETED",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 40,
    "results": results
})
print(run_score())

print("\nTesting E: Duplicate ID")
results.append({"question_id": "q0", "run_number": 1})
write_fixture({
    "status": "COMPLETED",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 41,
    "results": results
})
print(run_score())

