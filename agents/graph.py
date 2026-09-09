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
    
    workflow.add_edge("execute", "synthesize")
    
    workflow.add_edge("synthesize", "verify")
    workflow.add_edge("verify", "risk")
    workflow.add_edge("risk", END)
    
    return workflow.compile()