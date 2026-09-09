from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    run_id: str
    user_query: str
    task: str
    plan: Optional[Dict[str, Any]]
    current_step: int
    step_count: int
    retrieved_context: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]
    selected_model: str
    execution_events: List[str]
    final_answer: str
    verification_result: Optional[Dict[str, Any]]
    risk_result: Optional[Dict[str, Any]]
    human_review_required: bool
    status: str
    errors: List[str]
    timing: Dict[str, float]
    multimodal_results: List[Dict[str, Any]]
    input_files: List[str]
    file_analysis: List[Dict[str, Any]]
    uncertainties: List[str]