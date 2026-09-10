"""
Tool Registry module for SOVARA.
Allows registering, discovering, and executing tool functions by name.
"""

from typing import Callable, Dict, Any, Optional
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode

# Import Phase 1 Sandbox Tools
from tools.c_tools.sandbox.python_executor import execute_python

# Import Phase 2 File & Analysis Tools
from tools.c_tools.file_ops.file_manager import (
    read_file_content,
    write_file_content,
    list_workspace_directory,
    delete_workspace_file,
)
from tools.c_tools.analysis.csv_analyzer import analyze_csv
from tools.c_tools.analysis.excel_analyzer import analyze_excel

# Import Phase 3 Document & Validation Tools
from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown
from tools.c_tools.documents.pdf_generator import generate_pdf_report
from tools.c_tools.validation.output_validator import validate_tool_output
from tools.c_tools.validation.file_validator import validate_file_integrity


class ToolRegistry:
    """Central registry mapping tool names to executable functions."""

    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a new tool function by name."""
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = func

    def get(self, name: str) -> Optional[Callable[..., Any]]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def execute(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a registered tool by name with arguments."""
        tool = self.get(name)
        if not tool:
            return ExecutionResult(
                success=False,
                error=ExecutionError(
                    code=ErrorCode.INVALID_INPUT,
                    message=f"Tool '{name}' not found in registry.",
                ),
            ).to_dict()

        return tool(**kwargs)

    def list_tools(self) -> Dict[str, str]:
        """List all registered tools and their docstrings."""
        return {
            name: (func.__doc__ or "No description provided.").strip()
            for name, func in self._tools.items()
        }


# Global registry instance pre-populated with all SOVARA Phase 1, 2, and 3 tools
global_registry = ToolRegistry()

# Phase 1
global_registry.register("execute_python", execute_python)

# Phase 2
global_registry.register("read_file_content", read_file_content)
global_registry.register("write_file_content", write_file_content)
global_registry.register("list_workspace_directory", list_workspace_directory)
global_registry.register("delete_workspace_file", delete_workspace_file)
global_registry.register("analyze_csv", analyze_csv)
global_registry.register("analyze_excel", analyze_excel)

# Phase 3
global_registry.register("generate_docx", generate_docx)
global_registry.register("generate_pptx", generate_pptx)
global_registry.register("generate_markdown", generate_markdown)
global_registry.register("generate_pdf_report", generate_pdf_report)
global_registry.register("validate_tool_output", validate_tool_output)
global_registry.register("validate_file_integrity", validate_file_integrity)
