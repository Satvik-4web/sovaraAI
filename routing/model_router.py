from typing import Dict, Any

def route_model(task_type: str, vision_required: bool = False, reasoning_required: bool = False) -> Dict[str, str]:
    if vision_required:
        return {"model": None, "reason": "Vision capability unavailable", "capability": "vision"}
    if reasoning_required:
        return {"model": "qwen3:4b", "reason": "Complex reasoning required", "capability": "reasoning"}
    return {"model": "gemma3:4b", "reason": "General/simple task", "capability": "general"}