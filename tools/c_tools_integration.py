from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from tools.registry import registry

from tools.c_tools.sandbox.python_executor import execute_python
from tools.c_tools.file_ops.file_manager import read_file_content, write_file_content, list_workspace_directory, delete_workspace_file
from tools.c_tools.analysis.csv_analyzer import analyze_csv
from tools.c_tools.analysis.excel_analyzer import analyze_excel
from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pdf_generator import generate_pdf_report
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown

# Schemas
class ExecutePythonInput(BaseModel):
    code: str = Field(..., description="Python source code string to execute in the sandbox.")
    timeout: Optional[int] = Field(None, description="Optional timeout in seconds.")

class ReadFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to read, relative to workspace.")

class WriteFileInput(BaseModel):
    file_path: str = Field(..., description="Path to the file to write, relative to workspace.")
    content: str = Field(..., description="String content to write into the file.")

class ListDirectoryInput(BaseModel):
    directory_path: str = Field(".", description="Path to the directory to list, relative to workspace.")

class AnalyzeCsvInput(BaseModel):
    file_path: str = Field(..., description="Path to the CSV file to analyze.")
    delimiter: Optional[str] = Field(",", description="Delimiter character.")
    has_header: Optional[bool] = Field(True, description="Whether the CSV has a header row.")

class AnalyzeExcelInput(BaseModel):
    file_path: str = Field(..., description="Path to the Excel file to analyze.")
    sheet_name: Optional[str] = Field(None, description="Optional specific sheet name to read.")

class GenerateDocxInput(BaseModel):
    filename: str = Field(..., description="Output filename, e.g. 'report.docx'.")
    title: str = Field(..., description="Main document title.")
    sections: List[Dict[str, Any]] = Field(..., description="List of section dictionaries containing heading, content, bullet_points, table.")

class GeneratePdfInput(BaseModel):
    filename: str = Field(..., description="Output filename, e.g. 'report.pdf'.")
    title: str = Field(..., description="Main document title.")
    sections: List[Dict[str, Any]] = Field(..., description="List of section dictionaries containing heading, content, bullet_points, table.")

class GeneratePptxInput(BaseModel):
    filename: str = Field(..., description="Output filename, e.g. 'presentation.pptx'.")
    title: str = Field(..., description="Main presentation title.")
    slides: List[Dict[str, Any]] = Field(..., description="List of slide dictionaries containing title, content, bullet_points.")

class GenerateMarkdownInput(BaseModel):
    filename: str = Field(..., description="Output filename, e.g. 'report.md'.")
    title: str = Field(..., description="Main document title.")
    sections: List[Dict[str, Any]] = Field(..., description="List of section dictionaries containing heading, content, bullet_points, table.")

# Wrappers (in case we need to cast input types or handle execution differences)
def _execute_python(**kwargs): return execute_python(**kwargs)
def _read_file(**kwargs): return read_file_content(**kwargs)
def _write_file(**kwargs): return write_file_content(**kwargs)
def _list_files(**kwargs): return list_workspace_directory(**kwargs)
def _analyze_csv(**kwargs): return analyze_csv(**kwargs)
def _analyze_excel(**kwargs): return analyze_excel(**kwargs)
def _generate_docx(**kwargs): return generate_docx(**kwargs)
def _generate_pdf(**kwargs): return generate_pdf_report(**kwargs)
def _generate_pptx(**kwargs): return generate_pptx(**kwargs)
def _generate_markdown(**kwargs): return generate_markdown(**kwargs)

# Registration
registry.register("execute_python", "Executes Python code safely inside an isolated sandbox.", _execute_python, ExecutePythonInput, dict)
registry.register("read_file", "Reads the textual content of a file securely from the workspace.", _read_file, ReadFileInput, dict)
registry.register("write_file", "Writes textual content to a file securely within the workspace.", _write_file, WriteFileInput, dict)
registry.register("list_files", "Lists the contents of a directory securely within the workspace.", _list_files, ListDirectoryInput, dict)
registry.register("analyze_csv", "Safely parses, analyzes, and profiles a CSV file.", _analyze_csv, AnalyzeCsvInput, dict)
registry.register("analyze_excel", "Safely parses, analyzes, and profiles an Excel workbook (.xlsx/.xls).", _analyze_excel, AnalyzeExcelInput, dict)
registry.register("generate_docx", "Generates a structured Word (.docx) document with text, lists, and tables.", _generate_docx, GenerateDocxInput, dict)
registry.register("generate_pdf", "Generates a structured PDF report with text, lists, and tables.", _generate_pdf, GeneratePdfInput, dict)
registry.register("generate_pptx", "Generates a PowerPoint (.pptx) presentation with text and bullet lists.", _generate_pptx, GeneratePptxInput, dict)
registry.register("generate_markdown", "Generates a structured Markdown (.md) document.", _generate_markdown, GenerateMarkdownInput, dict)

print("Successfully registered C tools!")
