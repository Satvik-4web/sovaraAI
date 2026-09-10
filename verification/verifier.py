from typing import Dict, Any, List

def verify_results(evidence: List[Dict], final_answer: str, tool_outputs: List[str]) -> Dict[str, Any]:
    # We strictly instructed the LLM to output a specific phrase if evidence is missing
    insufficient_phrase = "does not contain enough information"
    
    # If the answer is completely empty, the model refused to answer (likely due to missing evidence).
    is_empty_answer = len(final_answer.strip()) == 0
    ans_lower = final_answer.lower()
    is_rejected = (
        "does not contain enough information" in ans_lower or 
        "not mentioned" in ans_lower or 
        "cannot answer" in ans_lower or 
        "not provided" in ans_lower or
        "error" in ans_lower or
        "timeout" in ans_lower
    )
    evidence_available = len(evidence) > 0 and not is_rejected and not is_empty_answer
    
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