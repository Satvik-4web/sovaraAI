import time
import json
from main import run_sovara_task

tests = [
    {
        "name": "1. RAG",
        "query": "What inspection procedure is specified for abnormal pump vibration?",
        "files": []
    },
    {
        "name": "2. Excel",
        "query": "Which pump has the highest recorded vibration?",
        "files": ["demo/pump_inspection.xlsx"]
    },
    {
        "name": "3. Out-of-KB",
        "query": "What is the maximum allowable pressure of Pump P-999?",
        "files": []
    }
]

for t in tests:
    print(f"\n{'='*50}\nTEST: {t['name']}\nQUERY: {t['query']}")
    t0 = time.time()
    res = run_sovara_task(t['query'], files=t['files'])
    total_time = time.time() - t0
    
    print(f"Selected Route: {res.get('routing', {}).get('routing_method')}")
    print(f"Planner Invoked: {res.get('routing', {}).get('planner_invoked')}")
    print(f"Tools Executed: {[step.get('action') for step in res.get('plan', [])]}")
    
    # Check what tool results were actually returned from auto-routing or executor
    delivs = res.get('deliverables', [])
    tools_actual = []
    for d in delivs:
        if isinstance(d, dict) and 'tool' in d: tools_actual.append(d['tool'])
    if tools_actual:
        print(f"Actual Tools Processed: {tools_actual}")
        
    print(f"Retrieved Evidence: {len(res.get('evidence', []))} chunks")
    print(f"Final Answer: {res.get('answer', '')}")
    
    verification = res.get('verification', {})
    print(f"Verification Result: {verification.get('verification_status')}")
    print(f"Issues: {verification.get('issues', [])}")
    print(f"Risk Result: {res.get('risk', {}).get('risk_level')}")
    print(f"Total Latency: {total_time:.2f}s")
