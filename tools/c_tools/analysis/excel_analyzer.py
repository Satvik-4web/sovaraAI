"""
Excel Data Analyzer module providing workbook sheet inspection, formula detection, and preview profiling.
Supports .xlsx files via openpyxl.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def analyze_excel(
    file_path: str,
    sheet_name: Optional[str] = None,
    preview_rows: int = 5,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyzes an Excel workbook file, extracting sheet lists, active sheet structure, formula counts, and data samples.

    Args:
        file_path: Path to the target Excel file (.xlsx).
        sheet_name: Optional specific sheet name to analyze. Defaults to the active sheet.
        preview_rows: Number of sample rows to include in the preview.
        workspace_root: Optional workspace root override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()

    try:
        validated_path = validate_workspace_path(file_path, workspace_root)
    except ValueError as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(code=ErrorCode.PATH_TRAVERSAL_ATTEMPT, message=str(e)),
        ).to_dict()

    if not validated_path.exists():
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_NOT_FOUND,
                message=f"Excel file not found: '{file_path}'",
            ),
        ).to_dict()

    # Verify openpyxl availability
    try:
        import openpyxl
    except ImportError:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.INVALID_FILE_FORMAT,
                message="The 'openpyxl' package is required to inspect Excel files. Install via 'pip install openpyxl'.",
            ),
        ).to_dict()

    try:
        wb = openpyxl.load_workbook(validated_path, data_only=False, read_only=True)
        sheet_names = wb.sheetnames

        target_sheet_name = sheet_name or sheet_names[0]
        if target_sheet_name not in sheet_names:
            wb.close()
            return ExecutionResult(
                success=False,
                execution_time=time.perf_counter() - start_time,
                error=ExecutionError(
                    code=ErrorCode.INVALID_INPUT,
                    message=f"Sheet '{target_sheet_name}' not found in workbook. Available sheets: {sheet_names}",
                ),
            ).to_dict()

        ws = wb[target_sheet_name]
        
        rows_iter = ws.iter_rows(values_only=False)
        try:
            first_row = next(rows_iter)
            headers = [str(cell.value) if cell.value is not None else f"Column_{i+1}" for i, cell in enumerate(first_row)]
        except StopIteration:
            wb.close()
            return ExecutionResult(
                success=True,
                result={
                    "file_name": validated_path.name,
                    "sheet_names": sheet_names,
                    "active_sheet": target_sheet_name,
                    "row_count": 0,
                    "column_count": 0,
                    "formula_count": 0,
                    "preview": [],
                },
                execution_time=time.perf_counter() - start_time,
            ).to_dict()

        row_count = 0
        formula_count = 0
        preview_data: List[Dict[str, Any]] = []

        for row in rows_iter:
            row_count += 1
            row_dict: Dict[str, Any] = {}

            for idx, cell in enumerate(row):
                if idx < len(headers):
                    col_name = headers[idx]
                    val = cell.value
                    val_str = str(val) if val is not None else ""

                    if isinstance(val_str, str) and val_str.startswith("="):
                        formula_count += 1

                    if row_count <= preview_rows:
                        row_dict[col_name] = val_str

            if row_count <= preview_rows:
                preview_data.append(row_dict)

        wb.close()
        exec_time = time.perf_counter() - start_time

        return ExecutionResult(
            success=True,
            result={
                "file_name": validated_path.name,
                "sheet_names": sheet_names,
                "active_sheet": target_sheet_name,
                "row_count": row_count,
                "column_count": len(headers),
                "formula_count": formula_count,
                "columns": headers,
                "preview": preview_data,
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.INVALID_FILE_FORMAT,
                message=f"Failed to analyze Excel file '{file_path}': {str(e)}",
            ),
        ).to_dict()
