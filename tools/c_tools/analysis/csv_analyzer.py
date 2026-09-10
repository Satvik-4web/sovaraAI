"""
CSV Data Analyzer module providing safe CSV parsing, metadata extraction, and profiling.
Uses Python standard library csv module with fallback support for pandas.
"""

import csv
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def _infer_type(value: str) -> str:
    """Helper to infer primitive data type from string representation."""
    val = value.strip()
    if not val:
        return "empty"
    if val.lower() in ("true", "false"):
        return "bool"
    try:
        int(val)
        return "int"
    except ValueError:
        pass
    try:
        float(val)
        return "float"
    except ValueError:
        pass
    return "string"


def analyze_csv(
    file_path: str,
    preview_rows: int = 5,
    delimiter: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parses a CSV file safely and extracts dataset structure, metadata, column summary, and row samples.

    Args:
        file_path: Path to the target CSV file.
        preview_rows: Number of initial sample rows to include in the preview (default: 5).
        delimiter: Optional explicit CSV delimiter character (e.g. ',', ';', '\t').
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
                message=f"CSV file not found: '{file_path}'",
            ),
        ).to_dict()

    try:
        with open(validated_path, "r", encoding="utf-8", errors="replace") as f:
            # Sniff delimiter if not specified
            sample_header = f.read(4096)
            f.seek(0)

            delim = delimiter
            if not delim:
                try:
                    sniff = csv.Sniffer().sniff(sample_header, delimiters=",;\t|")
                    delim = sniff.delimiter
                except Exception:
                    delim = ","

            reader = csv.reader(f, delimiter=delim)
            try:
                headers = next(reader)
            except StopIteration:
                return ExecutionResult(
                    success=True,
                    result={
                        "path": str(validated_path.name),
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "preview": [],
                    },
                    execution_time=time.perf_counter() - start_time,
                ).to_dict()

            row_count = 0
            preview_data: List[Dict[str, Any]] = []
            null_counts: Dict[str, int] = {h: 0 for h in headers}
            type_counts: Dict[str, Dict[str, int]] = {h: {} for h in headers}

            for row in reader:
                row_count += 1
                row_dict: Dict[str, Any] = {}

                for idx, col_name in enumerate(headers):
                    val = row[idx] if idx < len(row) else ""
                    val_str = str(val).strip()

                    if not val_str:
                        null_counts[col_name] += 1
                    
                    t = _infer_type(val_str)
                    type_counts[col_name][t] = type_counts[col_name].get(t, 0) + 1

                    if row_count <= preview_rows:
                        row_dict[col_name] = val_str

                if row_count <= preview_rows:
                    preview_data.append(row_dict)

            # Summarize column metadata
            columns_meta = []
            for h in headers:
                # dominant type
                types_found = type_counts[h]
                dominant_type = max(types_found, key=types_found.get) if types_found else "string"
                columns_meta.append(
                    {
                        "name": h,
                        "inferred_type": dominant_type,
                        "null_count": null_counts[h],
                        "null_percentage": round((null_counts[h] / row_count * 100), 2) if row_count > 0 else 0.0,
                    }
                )

            exec_time = time.perf_counter() - start_time
            return ExecutionResult(
                success=True,
                result={
                    "file_name": validated_path.name,
                    "row_count": row_count,
                    "column_count": len(headers),
                    "delimiter_used": delim,
                    "columns": columns_meta,
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
                message=f"Failed to analyze CSV file '{file_path}': {str(e)}",
            ),
        ).to_dict()
