import pytest
from agents.planner import fast_route, generate_plan
from unittest.mock import patch
import time

def test_fast_router_rag():
    conf, plan = fast_route("What is the maintenance procedure?")
    assert conf >= 0.8
    assert plan["steps"][0]["action"] == "search"
    
def test_fast_router_calc():
    conf, plan = fast_route("calculate 500 * 20")
    assert conf >= 0.8
    assert plan["steps"][0]["action"] == "calculate"

def test_fast_router_excel():
    conf, plan = fast_route("analyze the dataset", ["data.csv"])
    assert conf >= 0.8
    assert plan["steps"][0]["action"] == "csv"

def test_fast_router_complex():
    conf, plan = fast_route("analyze image and cross reference with sop", ["pump_pid.png", "sop.pdf"])
    assert conf == 0.5 # Complex routing

@patch('agents.planner.requests.post')
def test_generate_plan_fast_bypass(mock_post):
    # Should not call LLM
    plan = generate_plan("calculate 500 * 20", "run-1")
    assert not mock_post.called
    assert plan["routing_method"] == "fast_router"
    assert plan["planner_invoked"] is False

@patch('agents.planner.requests.post')
def test_generate_plan_timeout_fallback(mock_post):
    # Mock timeout
    import requests
    mock_post.side_effect = requests.exceptions.Timeout("Timeout!")
    
    plan = generate_plan("analyze complex PID with SOP", "run-2", ["pid.png", "sop.pdf"])
    
    assert mock_post.called
    assert plan["routing_method"] == "fast_router_fallback"
    assert plan["planner_invoked"] is True
    assert plan["planner_timeout"] is True
    # The fallback should be the highest confidence capability for this input (multimodal + rag)
    assert len(plan["steps"]) > 0

