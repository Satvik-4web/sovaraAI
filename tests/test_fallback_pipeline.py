import pytest
from main import run_sovara_task
from unittest.mock import patch
import requests

def mock_post_handler(*args, **kwargs):
    url = args[0] if args else kwargs.get('url', '')
    json_data = kwargs.get('json', {})
    
    if "api/embeddings" in url:
        class MockResponse:
            def __init__(self):
                self.status_code = 200
            def json(self):
                # Return a dummy embedding of size 768 (nomic-embed-text size)
                return {"embedding": [0.0] * 768}
            def raise_for_status(self):
                pass
        return MockResponse()

    content = json_data.get('messages', [{}])[0].get('content', '')
    if "Return a JSON object with 'goal'" in content:
        raise requests.exceptions.Timeout("Timeout!")
        
    class MockResponse:
        def __init__(self):
            self.status_code = 200
        def json(self):
            return {"message": {"content": "Synthesized answer."}}
        def raise_for_status(self):
            pass
    return MockResponse()

@patch('requests.post', side_effect=mock_post_handler)
def test_fallback_pipeline_rag(mock_post):
    res = run_sovara_task("Analyze complex PID with SOP", files=["demo/pump_pid.png", "datasets/synthetic_plant/documents/P101_Maintenance_SOP.md"])
    assert res["success"] is True
    assert res["routing"]["routing_method"] in ["fast_router_fallback", "fast_router"]
    assert len(res["evidence"]) > 0, f"Evidence empty! Errors: {res.get('errors')}"

@patch('requests.post', side_effect=mock_post_handler)
def test_fallback_pipeline_excel(mock_post):
    res = run_sovara_task("Analyze dataset", files=["demo/pump_inspection.xlsx"])
    assert res["success"] is True
    assert res["routing"]["routing_method"] in ["fast_router_fallback", "fast_router"]
    assert "excel" in str(res["plan"]).lower() or any(d.get("tool") == "analyze_excel" for d in res.get("deliverables", []))
    assert res["answer"] is not None and len(res["answer"]) > 0
    assert len(res.get("deliverables", [])) > 0, "Expected deliverables for Excel task"
    assert res.get("verification") is not None, "Verification must run"
    assert res.get("risk") is not None, "Risk classification must remain intact"

@patch('requests.post', side_effect=mock_post_handler)
def test_fast_bypass_calculation(mock_post):
    res = run_sovara_task("calculate 500 * 20")
    
    # Ensure planner was bypassed entirely by verifying that ONLY synthesis was called
    calls = [c for c in mock_post.call_args_list if "api/chat" in (c[0][0] if c[0] else c[1].get('url', ''))]
    assert len(calls) == 1
    content = calls[0][1]['json']['messages'][0]['content']
    assert "Synthesize a concise final answer" in content
    
    assert res["routing"]["routing_method"] == "fast_router"
    assert res["routing"]["planner_invoked"] is False
    assert "calculate" in str(res["plan"]).lower()
