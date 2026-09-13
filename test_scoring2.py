import json
import subprocess

def write_fixture(data):
    with open("datasets/benchmark/benchmark_results.json", "w") as f:
        json.dump(data, f)

def run_score():
    res = subprocess.run(["python", "datasets/benchmark/scoring.py"], capture_output=True, text=True)
    if res.stderr:
        return "STDERR: " + res.stderr.strip()
    return res.stdout.strip()

print("Testing C: 40/40")
write_fixture({
    "status": "COMPLETED",
    "total_questions": 40,
    "total_executions_expected": 40,
    "completed_executions": 40,
    "results": [{"question_id": f"q{i}", "run_number": 1, "expected": {}, "actual": {"success": True, "risk": {"level": "LOW"}}, "latency_ms": 100} for i in range(40)]
})
print(run_score())
