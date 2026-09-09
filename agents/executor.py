import time
import requests
import json
from .state import AgentState
from routing.model_router import route_model
from tools.registry import registry
from Rag.search import search_knowledge

def understand_node(state: AgentState):
    state["task"] = state["user_query"]
    state["execution_events"].append("TASK_UNDERSTANDING completed")
    return state

def plan_node(state: AgentState):
    t0 = time.time()
    from .planner import generate_plan
    plan = generate_plan(state["user_query"], state["run_id"], state.get("input_files", []))
    state["plan"] = plan
    state["timing"]["planning_ms"] = (time.time() - t0) * 1000
    state["execution_events"].append("PLANNER_COMPLETED")
    return state

def select_action_node(state: AgentState):
    route = route_model(state["task"])
    state["selected_model"] = route["model"]
    state["execution_events"].append(f"MODEL_SELECTED: {route['model']}")
    return state

def execute_node(state: AgentState):
    t0 = time.time()
    
    # Automatic File Routing
    for file_path in state.get("input_files", []):
        ext = file_path.lower().split('.')[-1]
        try:
            if ext in ["png", "jpg", "jpeg"]:
                from multimodal.adapter import MultimodalAdapter
                if "pid" in file_path.lower():
                    res = MultimodalAdapter.analyze_pid(file_path)
                else:
                    res = MultimodalAdapter.analyze_image(file_path)
                state["tool_results"].append({"tool": "multimodal", "result": res})
                if res.get("uncertainties"): state["uncertainties"].extend(res.get("uncertainties"))
            elif ext == "pdf":
                from multimodal.adapter import MultimodalAdapter
                res = MultimodalAdapter.extract_text(file_path)
                state["tool_results"].append({"tool": "multimodal", "result": res})
                if res.get("uncertainties"): state["uncertainties"].extend(res.get("uncertainties"))
            elif ext in ["xlsx", "csv"]:
                res = registry.execute("analyze_excel", {"file_path": file_path})
                state["tool_results"].append({"tool": "excel", "result": res})
        except Exception as e:
            state["errors"].append(f"Auto-route error for {file_path}: {e}")
            
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    rag_ms = 0
    tool_ms = 0
    
    # We iterate over steps and execute deterministically
    for step in steps:
        cap = step.get("required_capability", "")
        action = step.get("action", "")
        args = step.get("args", {})
        
        if cap == "rag":
            rt0 = time.time()
            try:
                chunks = search_knowledge(state["user_query"], limit=3)
                state["retrieved_context"].extend(chunks)
                state["execution_events"].append(f"RAG_COMPLETED: retrieved {len(chunks)} chunks")
            except Exception as e:
                state["errors"].append(f"RAG failure: {e}")
            rag_ms += (time.time() - rt0) * 1000
            
        elif cap in ["python", "file", "excel", "multimodal"]:
            tt0 = time.time()
            try:
                if action == "calculate" or cap == "python":
                    res = registry.execute("calculate", args)
                    state["tool_results"].append({"tool": "calculate", "result": res})
                elif cap == "file":
                    res = registry.execute("write_file", args) if "write_file" in args else registry.execute("read_file", args)
                    state["tool_results"].append({"tool": "file", "result": res})
                elif cap == "multimodal":
                    from multimodal.adapter import MultimodalAdapter
                    if "image" in str(args).lower():
                        res = MultimodalAdapter.analyze_image(args.get("file_path", "unknown.png"))
                    else:
                        res = MultimodalAdapter.extract_text(args.get("file_path", "unknown.pdf"))
                    state["tool_results"].append({"tool": "multimodal", "result": res})
                    if res.get("uncertainties"):
                        state["uncertainties"].extend(res.get("uncertainties"))
                elif cap == "excel":
                    res = registry.execute("analyze_excel", args)
                    state["tool_results"].append({"tool": "excel", "result": res})
                else:
                    state["tool_results"].append({"tool": action, "result": "Tool not implemented"})
                state["execution_events"].append(f"TOOL_COMPLETED: {action}")
            except Exception as e:
                state["errors"].append(str(e))
            tool_ms += (time.time() - tt0) * 1000
            
    state["timing"]["rag_ms"] = state["timing"].get("rag_ms", 0) + rag_ms
    state["timing"]["tool_ms"] = state["timing"].get("tool_ms", 0) + tool_ms
    state["step_count"] += 1
    return state

def synthesize_node(state: AgentState):
    t0 = time.time()
    if not state.get("final_answer"):
        url = "http://localhost:11434/api/chat"
        system_prompt = "You are SOVARA. Synthesize a concise final answer based ONLY on the evidence and tool results. If no evidence is present for factual claims, state exactly: 'The available knowledge base does not contain enough information.'"
        
        evidence = "\\n".join([c.get("text", "") for c in state["retrieved_context"]])
        tool_res = "\\n".join([str(t["result"]) for t in state["tool_results"]])
        
        prompt = f"EVIDENCE:\\n{evidence}\\n\\nTOOL RESULTS:\\n{tool_res}\\n\\nQUERY: {state['user_query']}"
        
        payload = {
            "model": "qwen3:4b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "num_predict": 250,
                "temperature": 0.2
            }
        }
        try:
            resp = requests.post(url, json=payload, timeout=60)
            state["final_answer"] = resp.json()["message"]["content"]
        except Exception as e:
            state["final_answer"] = f"Synthesis error: {e}"
            
    state["timing"]["synthesis_ms"] = (time.time() - t0) * 1000
    state["execution_events"].append("OUTPUT_GENERATED")
    return state

def verify_node(state: AgentState):
    t0 = time.time()
    from verification.verifier import verify_results
    res = verify_results(state["retrieved_context"], state["final_answer"], [str(t) for t in state["tool_results"]])
    state["verification_result"] = res
    state["execution_events"].append("VERIFICATION_COMPLETED")
    state["timing"]["verification_ms"] = (time.time() - t0) * 1000
    return state

def risk_node(state: AgentState):
    t0 = time.time()
    from verification.risk import assess_risk
    res = assess_risk(state["verification_result"])
    state["risk_result"] = res
    state["human_review_required"] = res.get("human_review_required", False)
    state["execution_events"].append("RISK_ASSESSED")
    state["timing"]["risk_ms"] = (time.time() - t0) * 1000
    state["status"] = "COMPLETED"
    return state