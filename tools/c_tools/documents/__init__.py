"""
Document generation package providing automated Word (.docx), PowerPoint (.pptx), Markdown (.md), and PDF generation tools.
"""

from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown
from tools.c_tools.documents.pdf_generator import generate_pdf_report

__all__ = [
    "generate_docx",
    "generate_pptx",
    "generate_markdown",
    "generate_pdf_report",
]
