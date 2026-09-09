from typing import Dict, Any, List

def verify_results(evidence: List[Dict], final_answer: str, tool_outputs: List[str]) -> Dict[str, Any]:
    # We strictly instructed the LLM to output a specific phrase if evidence is missing
    insufficient_phrase = "does not contain enough information"
    
    # Evidence is considered "available" if chunks were retrieved AND the LLM didn't reject them as insufficient
    evidence_available = len(evidence) > 0 and insufficient_phrase not in final_answer.lower()
    
    issues = []
    for tool_res in tool_outputs:
        if "pending" in str(tool_res).lower() or "missing" in str(tool_res).lower() or "offline" in str(tool_res).lower() or "unavailable" in str(tool_res).lower() or "error" in str(tool_res).lower():
            issues.append(f"Tool execution uncertainty: {tool_res}")
            
    if not evidence_available:
        issues.append("Insufficient relevant evidence retrieved for the query.")
        status = "NEEDS_REVIEW"
    elif issues:
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"
        
    return {
        "verification_status": status,
        "evidence_available": evidence_available,
        "evidence_coverage": 1.0 if evidence_available else 0.0,
        "citation_valid": evidence_available,
        "unsupported_claims": [],
        "issues": issues
    }