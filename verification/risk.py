from typing import Dict, Any

def assess_risk(verification_result: Dict[str, Any]) -> Dict[str, Any]:
    status = verification_result.get("verification_status", "FAIL")
    evidence_available = verification_result.get("evidence_available", False)
    issues = verification_result.get("issues", [])
    
    # Deterministic mapping based on structured verification signals
    has_uncertainty = any("uncertain" in str(i).lower() or "missing" in str(i).lower() for i in issues)
    
    if not evidence_available or status in ["NEEDS_REVIEW", "FAIL"] or has_uncertainty:
        return {
            "risk_level": "HIGH",
            "reasons": issues,
            "human_review_required": True
        }
        
    return {
        "risk_level": "LOW",
        "reasons": [],
        "human_review_required": False
    }