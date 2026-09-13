import requests
res = requests.post("http://localhost:11434/api/generate", json={"model": "qwen3:4b", "prompt": "Hello", "stream": False}, timeout=10)
print(res.status_code, res.json())
