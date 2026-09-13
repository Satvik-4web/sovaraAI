def fix_main():
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the return dict and add the routing observability
    replacement = '''
    is_success = result_state["status"] == "COMPLETED"
    
    plan_dict = result_state.get("plan", {}) or {}
    routing_meta = {
        "routing_method": plan_dict.get("routing_method", "unknown"),
        "routing_confidence": plan_dict.get("routing_confidence", 0.0),
        "planner_invoked": plan_dict.get("planner_invoked", False),
        "planner_timeout": plan_dict.get("planner_timeout", False),
        "planner_latency_ms": plan_dict.get("planner_latency_ms", 0)
    }

    return {
        "success": is_success,
        "task_id": result_state["run_id"],
        "run_id": result_state["run_id"],
        "status": result_state["status"],
        "answer": result_state["final_answer"],
        "plan": plan_dict.get("steps", []),
        "routing": routing_meta,
'''
    
    content = content.replace('''
    is_success = result_state["status"] == "COMPLETED"

    return {
        "success": is_success,
        "task_id": result_state["run_id"],
        "run_id": result_state["run_id"],
        "status": result_state["status"],
        "answer": result_state["final_answer"],
        "plan": result_state.get("plan", {}).get("steps", []),
''', replacement)

    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    fix_main()
