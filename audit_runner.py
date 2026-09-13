import json
import time
from main import run_sovara_task

tests = [
    {
        "id": "TEST_A_Simple_RAG",
        "query": "What does the maintenance SOP say about abnormal vibration?",
        "files": ["datasets/synthetic_plant/documents/P101_Maintenance_SOP.md"]
    },
    {
        "id": "TEST_B_Single_Tool",
        "query": "What is the vibration of P-101?",
        "files": ["datasets/synthetic_plant/data/P101_Vibration_History.csv"]
    },
    {
        "id": "TEST_D_Cross_modal_P101",
        "query": "Analyze P-101 using the provided P&ID, inspection report, maintenance spreadsheet and maintenance procedure. Identify abnormal conditions, perform any required calculations, assess risk, and prepare an approval recommendation.",
        "files": ["demo/pump_pid.png", "demo/inspection_report.pdf", "datasets/synthetic_plant/data/P101_Vibration_History.csv", "datasets/synthetic_plant/documents/P101_Maintenance_SOP.md"]
    },
    {
        "id": "TEST_E_Out_of_KB",
        "query": "What is the maximum allowable pressure for Pump P-999?",
        "files": []
    }
]

results = []

for t in tests:
    print(f"\\n=== Running {t['id']} ===")
    res = run_sovara_task(t['query'], files=t.get('files', []))
    
    out = {
        "id": t['id'],
        "success": res.get("success"),
        "plan": res.get("plan"),
        "models_used": res.get("models_used"),
        "verification": res.get("verification"),
        "risk": res.get("risk")
    }
    results.append(out)
    print(json.dumps(out, indent=2))

with open('datasets/benchmark/audit_results.json', 'w') as f:
    json.dump(results, f, indent=2)

