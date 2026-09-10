"""
SOVARA Multimodal Intelligence Subsystem

Public API for the SOVARA orchestrator.

Usage:
    from multimodal import extract_text, analyze_image, analyze_document, analyze_pid

    # Extract text from any document or image
    result = extract_text("report.pdf")

    # Analyze an image with the local VLM
    result = analyze_image("inspection.jpg")

    # Full document analysis (text + OCR + VLM)
    result = analyze_document("scanned_report.pdf")

    # P&ID / engineering drawing analysis
    result = analyze_pid("process_pid.png")

    # Visual question answering
    result = answer_visual_question("pid.png", "What equipment is downstream of P-101?")

    # Multi-document analysis
    result = analyze_documents(["pid.png", "report.pdf"], "Find issues with P-101")

    # Reasoning over evidence
    result = reason_about_evidence(evidence_list, "Analyze recurring failures")

All functions return Pydantic models (see schemas.py) that serialize
to predictable JSON. The orchestrator should never need to look inside
the multimodal package — these functions are the entire interface.
"""

from multimodal.pipeline import (
    analyze_document,
    analyze_documents,
    analyze_image,
    analyze_pid,
    answer_visual_question,
    extract_text,
    reason_about_evidence,
)

__all__ = [
    "extract_text",
    "analyze_image",
    "analyze_document",
    "analyze_pid",
    "answer_visual_question",
    "analyze_documents",
    "reason_about_evidence",
]

__version__ = "0.2.0"
