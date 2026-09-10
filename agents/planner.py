import json
import requests
import time
from typing import Dict, Any

def generate_plan(query: str, run_id: str, input_files: list = None, model: str = "qwen3:4b") -> Dict[str, Any]:
    url = "http://localhost:11434/api/chat"
    system = """Return a JSON object with 'goal' (string) and 'steps' (list of objects with 'id', 'action', 'required_capability', and optionally 'args' as a dictionary if the action requires tool arguments). 
Capabilities: rag, python, excel, file, multimodal, general, generate_docx.
Output ONLY valid JSON. Keep it extremely concise. Max 5 steps."""
    
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
        return parsed
    except Exception as e:
        return {"goal": "fallback", "steps": [{"id": 1, "action": "generic_response", "required_capability": "rag"}]}