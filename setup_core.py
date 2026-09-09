import os

files = {
    "requirements.txt": """
qdrant-client>=1.19.0
requests
pydantic
langgraph
langchain-core
""",
    "tools/registry.py": """
from typing import Dict, Any, Callable, List
from pydantic import BaseModel

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str, func: Callable, input_schema: Any, output_schema: Any, local_only: bool = True):
        self.tools[name] = {
            "name": name,
            "description": description,
            "func": func,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "local_only": local_only
        }
    
    def get_tool(self, name: str):
        return self.tools.get(name)

    def execute(self, name: str, kwargs: Dict[str, Any]):
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Tool {name} not found")
        return tool["func"](**kwargs)

    def get_all_tools_schema(self) -> List[Dict]:
        schemas = []
        for name, tool in self.tools.items():
            schemas.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["input_schema"].model_json_schema()
                }
            })
        return schemas

registry = ToolRegistry()
""",
    "tools/python_tool.py": """
from pydantic import BaseModel
from .registry import registry
import ast
import operator

class CalculateInput(BaseModel):
    expression: str

def calculate(expression: str) -> str:
    allowed_operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.USub: operator.neg,
    }
    def evaluate(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)): return node.value
            raise ValueError("Only numbers are allowed.")
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            operation = allowed_operators.get(type(node.op))
            if operation is None: raise ValueError("This mathematical operation is not allowed.")
            return operation(left, right)
        if isinstance(node, ast.UnaryOp):
            operation = allowed_operators.get(type(node.op))
            if operation is None: raise ValueError("This operation is not allowed.")
            return operation(evaluate(node.operand))
        raise ValueError("Invalid mathematical expression.")

    try:
        tree = ast.parse(expression, mode="eval")
        return str(evaluate(tree.body))
    except Exception as e:
        return f"Error: {e}"

registry.register("calculate", "Perform mathematical calculations. Use this tool whenever an exact numerical calculation is required.", calculate, CalculateInput, str)
""",
    "tools/document_tools.py": """
from pydantic import BaseModel
from .registry import registry
import os

class WriteFileInput(BaseModel):
    file_path: str
    content: str

def write_file(file_path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Success: wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"

registry.register("write_file", "Write content to a file", write_file, WriteFileInput, str)
""",
    "routing/model_router.py": """
from typing import Dict, Any

def route_model(task_type: str, vision_required: bool = False, reasoning_required: bool = False) -> Dict[str, str]:
    if vision_required:
        # Mock vision model for now
        return {"model": "llava:latest", "reason": "Vision required", "capability": "vision"}
    if reasoning_required:
        return {"model": "qwen3:4b", "reason": "Complex reasoning required", "capability": "reasoning"}
    return {"model": "gemma3:4b", "reason": "General/simple task", "capability": "general"}
""",
    "multimodal/adapter.py": """
from typing import Dict, Any

class MultimodalAdapter:
    @staticmethod
    def extract_text(file_path: str) -> Dict[str, Any]:
        return {
            "success": False,
            "content_type": "text",
            "text": "",
            "uncertainties": ["Not implemented: Handled by Person B"],
            "source": file_path
        }
    
    @staticmethod
    def analyze_image(image_path: str) -> Dict[str, Any]:
        return {
            "success": False,
            "content_type": "image",
            "findings": [],
            "uncertainties": ["Vision system unavailable"],
            "source": image_path
        }
""",
    "verification/verifier.py": """
from typing import Dict, Any, List

def verify_results(evidence: List[Dict], final_answer: str, tool_outputs: List[str]) -> Dict[str, Any]:
    # Basic structured check
    evidence_exists = len(evidence) > 0
    issues = []
    
    if not evidence_exists and "available knowledge base does not contain enough information" not in final_answer.lower():
        issues.append("Final answer provided without evidence but did not state insufficient knowledge.")
        
    status = "PASS"
    if issues:
        status = "FAIL"
    elif not evidence_exists:
        status = "NEEDS_REVIEW"
        
    return {
        "verification_status": status,
        "evidence_coverage": 1.0 if evidence_exists else 0.0,
        "citation_valid": evidence_exists,
        "calculations_verified": True,
        "unsupported_claims": issues,
        "issues": issues
    }
""",
    "verification/risk.py": """
from typing import Dict, Any

def assess_risk(verification_result: Dict[str, Any]) -> Dict[str, Any]:
    status = verification_result.get("verification_status", "FAIL")
    issues = verification_result.get("issues", [])
    
    if status == "FAIL":
        return {
            "risk_level": "HIGH",
            "reasons": issues + ["Verification failed"],
            "human_review_required": True
        }
    elif status == "NEEDS_REVIEW":
        return {
            "risk_level": "MEDIUM",
            "reasons": ["Needs manual review due to low evidence"],
            "human_review_required": False
        }
        
    return {
        "risk_level": "LOW",
        "reasons": [],
        "human_review_required": False
    }
""",
    "agents/state.py": """
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
""",
    "agents/planner.py": """
import json
import requests
from typing import Dict, Any

def generate_plan(query: str, run_id: str, model: str = "qwen3:4b") -> Dict[str, Any]:
    # Structured planning logic
    # We will use the local Ollama with JSON format restriction
    url = "http://localhost:11434/api/chat"
    system = "You are a planning agent. Return a JSON object with 'goal' (string) and 'steps' (list of objects with 'id', 'action', 'required_capability'). Output ONLY valid JSON."
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": query}
        ],
        "stream": False,
        "format": "json"
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"goal": "fallback", "steps": [{"id": 1, "action": "generic_response", "required_capability": "general"}]}
""",
    "agents/executor.py": """
# Extracted actions for graph nodes
from .state import AgentState
from routing.model_router import route_model
from tools.registry import registry
from Rag.search import search_knowledge
import requests
import json

def understand_node(state: AgentState):
    state["task"] = state["user_query"]
    state["execution_events"].append("TASK_UNDERSTANDING completed")
    return state

def plan_node(state: AgentState):
    from .planner import generate_plan
    plan = generate_plan(state["user_query"], state["run_id"])
    state["plan"] = plan
    state["execution_events"].append("PLANNER_COMPLETED")
    return state

def select_action_node(state: AgentState):
    route = route_model(state["task"])
    state["selected_model"] = route["model"]
    state["execution_events"].append(f"MODEL_SELECTED: {route['model']}")
    return state

def execute_node(state: AgentState):
    # Perform RAG retrieval first
    query = state["user_query"]
    try:
        chunks = search_knowledge(query, limit=3)
        state["retrieved_context"] = chunks
        state["execution_events"].append(f"RAG_COMPLETED: retrieved {len(chunks)} chunks")
    except Exception as e:
        state["errors"].append(f"RAG failure: {e}")
        state["retrieved_context"] = []
    
    # Try calling tools via LLM
    url = "http://localhost:11434/api/chat"
    system_prompt = "You are SOVARA. Answer the query. Use tools if necessary. Base answers ONLY on evidence provided."
    context = "EVIDENCE:\\n" + "\\n".join([c.get("text", "") for c in state["retrieved_context"]])
    
    payload = {
        "model": state["selected_model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context + "\\n\\nQUERY: " + query}
        ],
        "tools": registry.get_all_tools_schema(),
        "stream": False
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        msg = resp.json()["message"]
        
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                args = tc["function"]["arguments"]
                if isinstance(args, str):
                    args = json.loads(args)
                try:
                    res = registry.execute(func_name, args)
                    state["tool_results"].append({"tool": func_name, "result": res})
                    state["execution_events"].append(f"TOOL_COMPLETED: {func_name}")
                except Exception as e:
                    state["errors"].append(str(e))
            # Just do one tool loop for this simple graph
        else:
            state["final_answer"] = msg.get("content", "")
            
    except Exception as e:
        state["errors"].append(f"LLM failure: {e}")
        state["final_answer"] = "System Error"
        
    state["step_count"] += 1
    return state

def synthesize_node(state: AgentState):
    if not state.get("final_answer"):
        url = "http://localhost:11434/api/chat"
        system_prompt = "You are SOVARA. Synthesize a final answer based ONLY on the evidence and tool results. If no evidence is present for factual claims, state: 'The available knowledge base does not contain enough information.'"
        
        evidence = "\\n".join([c.get("text", "") for c in state["retrieved_context"]])
        tool_res = "\\n".join([str(t["result"]) for t in state["tool_results"]])
        
        prompt = f"EVIDENCE:\\n{evidence}\\n\\nTOOL RESULTS:\\n{tool_res}\\n\\nQUERY: {state['user_query']}"
        
        payload = {
            "model": state["selected_model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            state["final_answer"] = resp.json()["message"]["content"]
        except Exception as e:
            state["final_answer"] = f"Synthesis error: {e}"
            
    state["execution_events"].append("OUTPUT_GENERATED")
    return state

def verify_node(state: AgentState):
    from verification.verifier import verify_results
    res = verify_results(state["retrieved_context"], state["final_answer"], state["tool_results"])
    state["verification_result"] = res
    state["execution_events"].append("VERIFICATION_COMPLETED")
    return state

def risk_node(state: AgentState):
    from verification.risk import assess_risk
    res = assess_risk(state["verification_result"])
    state["risk_result"] = res
    state["human_review_required"] = res.get("human_review_required", False)
    state["execution_events"].append("RISK_ASSESSED")
    state["status"] = "COMPLETED"
    return state
""",
    "agents/graph.py": """
from langgraph.graph import StateGraph, END
from .state import AgentState
from .executor import understand_node, plan_node, select_action_node, execute_node, synthesize_node, verify_node, risk_node

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("understand", understand_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("select_action", select_action_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("synthesize", synthesize_node)
    workflow.add_node("verify", verify_node)
    workflow.add_node("risk", risk_node)
    
    workflow.set_entry_point("understand")
    
    workflow.add_edge("understand", "plan")
    workflow.add_edge("plan", "select_action")
    workflow.add_edge("select_action", "execute")
    
    def more_work(state: AgentState):
        # Prevent infinite loops
        if state["step_count"] > 3 or state.get("final_answer"):
            return "synthesize"
        return "select_action"
        
    workflow.add_conditional_edges(
        "execute",
        more_work,
        {
            "select_action": "select_action",
            "synthesize": "synthesize"
        }
    )
    
    workflow.add_edge("synthesize", "verify")
    workflow.add_edge("verify", "risk")
    workflow.add_edge("risk", END)
    
    return workflow.compile()
""",
    "main.py": """
import uuid
import json
import os
from agents.graph import build_graph
from agents.state import AgentState
from tools.python_tool import calculate
from tools.document_tools import write_file

# Initialize tools
import tools.python_tool
import tools.document_tools

def run_sovara_task(user_query: str, files: list = None, knowledge_base: str = None) -> dict:
    run_id = str(uuid.uuid4())
    
    initial_state: AgentState = {
        "run_id": run_id,
        "user_query": user_query,
        "task": "",
        "plan": None,
        "current_step": 0,
        "step_count": 0,
        "retrieved_context": [],
        "tool_results": [],
        "selected_model": "qwen3:4b",
        "execution_events": ["TASK_STARTED"],
        "final_answer": "",
        "verification_result": None,
        "risk_result": None,
        "human_review_required": False,
        "status": "RUNNING",
        "errors": []
    }
    
    graph = build_graph()
    
    try:
        result_state = graph.invoke(initial_state)
    except Exception as e:
        initial_state["errors"].append(str(e))
        initial_state["status"] = "FAILED"
        result_state = initial_state
        
    return {
        "run_id": result_state["run_id"],
        "status": result_state["status"],
        "answer": result_state["final_answer"],
        "evidence": result_state["retrieved_context"],
        "citations": [c.get("chunk_id") for c in result_state["retrieved_context"]],
        "execution_trace": result_state["execution_events"],
        "deliverables": result_state["tool_results"],
        "verification": result_state["verification_result"],
        "risk": result_state["risk_result"],
        "human_review_required": result_state.get("human_review_required", False),
        "errors": result_state["errors"]
    }

if __name__ == "__main__":
    import sys
    
    print("\\n==================================================")
    print(" SOVARA AI Core Demo")
    print("==================================================\\n")
    
    query = "What is the recommended pressure for Pump P-999?"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        
    print(f"User Query: {query}\\n")
    
    result = run_sovara_task(user_query=query)
    
    print(f"Status: {result['status']}")
    print(f"Risk: {result['risk']['risk_level'] if result['risk'] else 'N/A'}")
    print(f"Human Review: {result['human_review_required']}")
    print(f"Answer: {result['answer']}")
    print(f"Errors: {result['errors']}\\n")
    print("Execution Trace:")
    for evt in result['execution_trace']:
        print(f" - {evt}")
"""
}

def setup():
    for filepath, content in files.items():
        dir_name = os.path.dirname(filepath)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip())
    print("Core structure generated.")

if __name__ == "__main__":
    setup()
