import json
import time
from main import run_sovara_task

tests = [
    {
        "id": 1,
        "name": "grounded_rag",
        "query": "Why is the pump vibrating?",
        "expected_risk": "LOW"
    },
    {
        "id": 2,
        "name": "out_of_knowledge",
        "query": "What is the recommended pressure for Pump P-999?",
        "expected_risk": "HIGH"
    },
    {
        "id": 3,
        "name": "citation_correctness",
        "query": "What is the daily inspection schedule?",
        "expected_risk": "LOW"
    },
    {
        "id": 4,
        "name": "hallucination_prevention",
        "query": "Who manufactured the pump?",
        "expected_risk": "HIGH"
    },
    {
        "id": 5,
        "name": "calculation",
        "query": "Calculate 15 multiplied by 24.",
        "expected_risk": "LOW"
    },
    {
        "id": 6,
        "name": "tool_selection",
        "query": "Write the word 'TEST' to a file named 'demo/test.txt'.",
        "expected_risk": "LOW"
    },
    {
        "id": 7,
        "name": "spreadsheet",
        "query": "Analyze this spreadsheet.",
        "files": ["demo/pump_inspection.xlsx"],
        "expected_risk": "LOW"
    },
    {
        "id": 8,
        "name": "image_input",
        "query": "What is in this image?",
        "files": ["demo/pump_pid.png"],
        "expected_risk": "HIGH" # Vision unavailable or uncertain
    },
    {
        "id": 9,
        "name": "p_and_id",
        "query": "Extract labels from this P&ID.",
        "files": ["demo/pump_pid.png"],
        "expected_risk": "HIGH" # Vision unavailable or uncertain
    },
    {
        "id": 10,
        "name": "verification_risk_escalation",
        "query": "Analyze the pump inspection information, examine the engineering drawing, retrieve relevant maintenance guidance from the internal knowledge base, analyze the inspection measurements, identify potential issues, perform required calculations, verify the evidence, assess risk, and prepare an engineering approval note.",
        "files": ["demo/inspection_report.pdf", "demo/pump_inspection.xlsx", "demo/pump_pid.png"],
        "expected_risk": "HIGH" # Triggered by vision uncertainty
    }
]

def run_evaluation():
    results = []
    print("========================================")
    print(" SOVARA EVALUATION SUITE")
    print("========================================")
    for test in tests:
        print(f"\\nRunning Test {test['id']}: {test['name']}")
        t0 = time.time()
        res = run_sovara_task(test["query"], files=test.get("files", []))
        latency = time.time() - t0
        
        actual_risk = res["risk"]["risk_level"] if res.get("risk") else "UNKNOWN"
        passed = actual_risk == test["expected_risk"]
        
        results.append({
            "id": test["id"],
            "name": test["name"],
            "pass": passed,
            "latency": latency,
            "risk": actual_risk
        })
        print(f"Result: {'PASS' if passed else 'FAIL'} (Expected {test['expected_risk']}, Got {actual_risk}) in {latency:.2f}s")
        
    with open("evaluation/results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\\n========================================")
    print(" EVALUATION SUMMARY")
    print("========================================")
    passed_count = sum(1 for r in results if r["pass"])
    print(f"Passed: {passed_count}/{len(results)}")
    print("Results saved to evaluation/results.json")

if __name__ == "__main__":
    run_evaluation()
