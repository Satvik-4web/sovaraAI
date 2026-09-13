import json
import requests
import time
from typing import Dict, Any

def fast_route(query: str, input_files: list = None) -> Dict[str, Any]:
    # Returns (confidence, plan)
    q_lower = query.lower()
    files = input_files or []
    
    # 1. Image / P&ID tasks
    if any(f.endswith(('.png', '.jpg', '.jpeg')) for f in files) or "p&id" in q_lower or "image" in q_lower or "diagram" in q_lower:
        if len(files) <= 1:
            return 0.9, {"goal": "Analyze Image", "steps": [{"id": 1, "action": "multimodal", "required_capability": "multimodal"}]}
        else:
            return 0.5, {"goal": "Analyze Image and Retrieve", "steps": [{"id": 1, "action": "multimodal", "required_capability": "multimodal"}, {"id": 2, "action": "search", "required_capability": "rag"}]}
            
    # 2. Calculation / Python
    if "calculate" in q_lower or "compute" in q_lower or "average" in q_lower or "*" in q_lower or "+" in q_lower:
        if not files:
            return 0.9, {"goal": "Calculate", "steps": [{"id": 1, "action": "calculate", "required_capability": "python", "args": {"code": query}}]}
        elif any(f.endswith(('.xlsx', '.xls', '.csv')) for f in files):
            cap = "excel" if files[0].endswith('.xlsx') else "csv"
            return 0.85, {"goal": "Calculate on Spreadsheet", "steps": [{"id": 1, "action": cap, "required_capability": cap}, {"id": 2, "action": "calculate", "required_capability": "python", "args": {"code": query}}]}
            
    # 3. Excel / CSV
    if any(f.endswith(('.xlsx', '.xls', '.csv')) for f in files):
        cap = "excel" if files[0].endswith('.xlsx') else "csv"
        if len(files) <= 1:
            return 0.85, {"goal": "Analyze Spreadsheet", "steps": [{"id": 1, "action": cap, "required_capability": cap}]}
        else:
            return 0.5, {"goal": "Analyze Spreadsheet and Retrieve", "steps": [{"id": 1, "action": cap, "required_capability": cap}, {"id": 2, "action": "search", "required_capability": "rag"}]}

    # 4. RAG / Knowledge Retrieval (Default Fallback)
    return 0.85 if not files else 0.5, {"goal": "Retrieve Knowledge", "steps": [{"id": 1, "action": "search", "required_capability": "rag"}]}

def generate_plan(query: str, run_id: str, input_files: list = None, model: str = "qwen3:4b") -> Dict[str, Any]:
    url = "http://localhost:11434/api/chat"
    system = """Return a JSON object with 'goal' (string) and 'steps' (list of objects with 'id', 'action', 'required_capability', and optionally 'args' as a dictionary if the action requires tool arguments). 
Capabilities: rag, python, excel, file, multimodal, general, generate_docx.
Output ONLY valid JSON. Keep it extremely concise. Max 5 steps."""
    
    t0 = time.time()
    
    conf, fast_plan = fast_route(query, input_files)
    
    # 1. Bypass planner for simple tasks
    if conf >= 0.8 and fast_plan:
        fast_plan["routing_method"] = "fast_router"
        fast_plan["routing_confidence"] = conf
        fast_plan["planner_invoked"] = False
        fast_plan["planner_latency_ms"] = (time.time() - t0) * 1000
        fast_plan["planner_timeout"] = False
        return fast_plan
        
    files_str = f"\\nINPUT FILES: {', '.join(input_files)}" if input_files else ""
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query + files_str}
        ],
        "stream": False,
        "format": "json"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        parsed = json.loads(content)
        if "steps" in parsed and isinstance(parsed["steps"], list):
            valid_steps = []
            for i, step in enumerate(parsed["steps"]):
                if isinstance(step, str):
                    cap = "python" if "calculat" in step.lower() else "general"
                    valid_steps.append({"id": i+1, "action": step, "required_capability": cap, "args": {"expression": step}})
                else:
                    if "calculat" in step.get("action", "").lower() or "calculat" in str(step.get("args", "")).lower():
                        step["required_capability"] = "python"
                    if "write" in step.get("action", "").lower() or "file" in step.get("action", "").lower():
                        step["required_capability"] = "file"
                    valid_steps.append(step)
            parsed["steps"] = valid_steps
            
        parsed["routing_method"] = "llm_planner"
        parsed["routing_confidence"] = 1.0
        parsed["planner_invoked"] = True
        parsed["planner_latency_ms"] = (time.time() - t0) * 1000
        parsed["planner_timeout"] = False
        return parsed
    except Exception as e:
        print(f"PLANNER ERROR: {e}")
        # Use the highest confidence fast_route plan
        fallback_plan = fast_plan
        fallback_plan["routing_method"] = "fast_router_fallback"
        fallback_plan["routing_confidence"] = conf
        fallback_plan["planner_invoked"] = True
        fallback_plan["planner_latency_ms"] = (time.time() - t0) * 1000
        fallback_plan["planner_timeout"] = True
        return fallback_plan
