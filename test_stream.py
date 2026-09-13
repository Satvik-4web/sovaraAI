import requests
import json

s = requests.post("http://localhost:8000/api/chat/session")
sid = s.json()["session_id"]
print("Created session:", sid)

payload = {
    "message": "Say exactly: 'Per PUMP MAINTENANCE MANUAL Section causes between bearings supports'",
    "active_files": [],
    "exclude_files": []
}

resp = requests.post(f"http://localhost:8000/api/chat/message/{sid}", json=payload, stream=True)
for line in resp.iter_lines():
    if line:
        print(line.decode('utf-8'))
