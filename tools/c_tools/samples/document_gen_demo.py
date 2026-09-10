"""
Sample script demonstrating Word, PowerPoint, Markdown, and PDF document generation in SOVARA.
"""

import sys
import os
import json

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown
from tools.c_tools.documents.pdf_generator import generate_pdf_report

def main():
    print("--- 1. Generating Word (.docx) Document ---")
    sections = [
        {"heading": "Executive Summary", "content": "SOVARA Phase 3 Document Subsystem report."},
        {"heading": "Key Highlights", "bullet_points": ["Air-Gapped Compliance", "Zero External Mandate", "Structured Validation"]},
        {
            "heading": "Performance Metrics",
            "table": {
                "headers": ["Metric", "Value", "Status"],
                "rows": [["Execution Time", "0.05s", "Optimal"], ["Memory Usage", "12MB", "Low"]],
            },
        },
    ]
    res_docx = generate_docx("demo/report.docx", "Executive Project Briefing", sections)
    print(json.dumps(res_docx, indent=2))
    print()

    print("--- 2. Generating PowerPoint (.pptx) Presentation ---")
    slides = [
        {"title": "Architecture Overview", "bullet_points": ["Docker Sandbox", "Path Security Guard", "Document Generators"]},
        {"title": "Validation Layer", "content": "All tool outputs are schema-validated automatically before returning."},
    ]
    res_pptx = generate_pptx("demo/presentation.pptx", "SOVARA Executive Briefing", slides)
    print(json.dumps(res_pptx, indent=2))
    print()

    print("--- 3. Generating Markdown (.md) Document ---")
    res_md = generate_markdown(
        "demo/summary.md",
        "Subsystem Status Report",
        "## Subsystem Health\nAll modules operational.",
        metadata={"author": "Antigravity Assistant", "version": "1.0"},
    )
    print(json.dumps(res_md, indent=2))
    print()

    print("--- 4. Generating Printable PDF/HTML Report ---")
    res_pdf = generate_pdf_report("demo/printable_report.pdf", "Official Compliance Certificate", "This certifies that SOVARA Phase 3 has passed all security checks.")
    print(json.dumps(res_pdf, indent=2))

if __name__ == "__main__":
    main()
