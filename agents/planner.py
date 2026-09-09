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
        "format": "json",
        "options": {
            "num_predict": 250,
            "temperature": 0.1
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"goal": "fallback", "steps": [{"id": 1, "action": "generic_response", "required_capability": "rag"}]}