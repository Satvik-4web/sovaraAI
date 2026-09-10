"""
SOVARA Tools, Execution & Output Subsystem.
Standalone modular Python package for secure execution, file operations, data analysis, document generation, and output validation.
"""

from tools.c_tools.sandbox.python_executor import execute_python
from tools.c_tools.config import SandboxConfig
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.registry import global_registry, ToolRegistry

# File Operations
from tools.c_tools.file_ops.file_manager import (
    read_file_content,
    write_file_content,
    list_workspace_directory,
    delete_workspace_file,
)

# Data Analysis
from tools.c_tools.analysis.csv_analyzer import analyze_csv
from tools.c_tools.analysis.excel_analyzer import analyze_excel

# Document Generation
from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown
from tools.c_tools.documents.pdf_generator import generate_pdf_report

# Output & File Validation
from tools.c_tools.validation.output_validator import validate_tool_output
from tools.c_tools.validation.file_validator import validate_file_integrity

__all__ = [
    "execute_python",
    "SandboxConfig",
    "ExecutionResult",
    "ExecutionError",
    "ErrorCode",
    "global_registry",
    "ToolRegistry",
    "read_file_content",
    "write_file_content",
    "list_workspace_directory",
    "delete_workspace_file",
    "analyze_csv",
    "analyze_excel",
    "generate_docx",
    "generate_pptx",
    "generate_markdown",
    "generate_pdf_report",
    "validate_tool_output",
    "validate_file_integrity",
]
