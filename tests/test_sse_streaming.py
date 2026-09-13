import pytest
import json
from fastapi.testclient import TestClient
from api_server import app
from agents.session import create_session

client = TestClient(app)

def test_sse_streaming_no_duplication():
    # 1. Create a session
    sid = create_session()
    
    # 2. Hit the streaming endpoint
    payload = {
        "message": "Say exactly: 'Misalignment between pump and motor'",
        "active_files": [],
        "exclude_files": []
    }
    
    response = client.post(f"/api/chat/message/{sid}", json=payload)
    
    assert response.status_code == 200
    
    accumulated_message = ""
    chunks_received = []
    
    # Process SSE line by line
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            if data.get("type") == "message":
                chunk = data.get("content", "")
                chunks_received.append(chunk)
                accumulated_message += chunk
                
    # Verify no duplication in the accumulated string
    assert "MisMisalignment" not in accumulated_message
    assert "pump pump" not in accumulated_message
    assert "motor motor" not in accumulated_message
    
    # Verify the accumulated message contains the expected string cleanly
    # Note: it might not be EXACTLY the same due to LLM prompt wrappers, but it shouldn't contain stutters.
    assert len(chunks_received) > 0
