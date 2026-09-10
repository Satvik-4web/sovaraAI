"""
File Manager module providing secure read, write, list, and delete operations.
Enforces path traversal safety and file size constraints.
"""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

from tools.c_tools.config import DEFAULT_CONFIG
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def read_file_content(
    file_path: str,
    max_bytes: Optional[int] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reads the content of a file within the workspace boundary up to max_bytes limit.

    Args:
        file_path: Relative or absolute path to the file.
        max_bytes: Maximum number of bytes to read (defaults to config limit: 1MB).
        workspace_root: Optional workspace root directory override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()
    limit = max_bytes if max_bytes is not None else DEFAULT_CONFIG.max_file_read_bytes

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
                message=f"File not found: '{file_path}'",
            ),
        ).to_dict()

    if not validated_path.is_file():
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.INVALID_INPUT,
                message=f"Path is not a regular file: '{file_path}'",
            ),
        ).to_dict()

    try:
        file_size = validated_path.stat().st_size
        truncated = file_size > limit

        with open(validated_path, "rb") as f:
            raw_bytes = f.read(limit)

        # Attempt UTF-8 decoding with fallback
        try:
            content_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content_text = raw_bytes.decode("latin-1", errors="replace")

        exec_time = time.perf_counter() - start_time
        return ExecutionResult(
            success=True,
            stdout="",
            stderr="",
            result={
                "path": str(validated_path.name),
                "content": content_text,
                "size_bytes": file_size,
                "bytes_read": len(raw_bytes),
                "truncated": truncated,
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_OPERATION_ERROR,
                message=f"Error reading file '{file_path}': {str(e)}",
            ),
        ).to_dict()


def write_file_content(
    file_path: str,
    content: str,
    overwrite: bool = False,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Writes text content to a file within the workspace boundary.

    Args:
        file_path: Relative or absolute path to the target file.
        content: Text content to write.
        overwrite: If False, raises error if file already exists.
        workspace_root: Optional workspace root directory override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()

    if not isinstance(content, str):
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.INVALID_INPUT,
                message="Content to write must be a string.",
            ),
        ).to_dict()

    try:
        validated_path = validate_workspace_path(file_path, workspace_root)
    except ValueError as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(code=ErrorCode.PATH_TRAVERSAL_ATTEMPT, message=str(e)),
        ).to_dict()

    if validated_path.exists() and not overwrite:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_ALREADY_EXISTS,
                message=f"File already exists and overwrite is set to False: '{file_path}'",
            ),
        ).to_dict()

    try:
        validated_path.parent.mkdir(parents=True, exist_ok=True)
        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(content)

        exec_time = time.perf_counter() - start_time
        return ExecutionResult(
            success=True,
            result={
                "path": str(validated_path.name),
                "size_bytes": len(content.encode("utf-8")),
                "status": "written",
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_OPERATION_ERROR,
                message=f"Error writing to file '{file_path}': {str(e)}",
            ),
        ).to_dict()


def list_workspace_directory(
    subpath: str = ".",
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Lists files and subdirectories within a given workspace directory path.

    Args:
        subpath: Sub-directory path within the workspace root.
        workspace_root: Optional workspace root directory override.

    Returns:
        Structured ExecutionResult dictionary.
    """
    start_time = time.perf_counter()

    try:
        validated_path = validate_workspace_path(subpath, workspace_root)
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
                message=f"Directory not found: '{subpath}'",
            ),
        ).to_dict()

    if not validated_path.is_dir():
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.INVALID_INPUT,
                message=f"Path is not a directory: '{subpath}'",
            ),
        ).to_dict()

    try:
        entries: List[Dict[str, Any]] = []
        for item in validated_path.iterdir():
            stat = item.stat()
            entries.append(
                {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size_bytes": stat.st_size if item.is_file() else None,
                    "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                }
            )

        exec_time = time.perf_counter() - start_time
        return ExecutionResult(
            success=True,
            result={
                "directory": subpath,
                "total_items": len(entries),
                "items": entries,
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_OPERATION_ERROR,
                message=f"Error listing directory '{subpath}': {str(e)}",
            ),
        ).to_dict()


def delete_workspace_file(
    file_path: str,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deletes a target file or empty directory within the workspace boundary.

    Args:
        file_path: Relative or absolute path to the file/directory.
        workspace_root: Optional workspace root directory override.

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
                message=f"File not found: '{file_path}'",
            ),
        ).to_dict()

    try:
        if validated_path.is_file():
            validated_path.unlink()
        elif validated_path.is_dir():
            validated_path.rmdir()

        exec_time = time.perf_counter() - start_time
        return ExecutionResult(
            success=True,
            result={
                "path": file_path,
                "status": "deleted",
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_OPERATION_ERROR,
                message=f"Error deleting path '{file_path}': {str(e)}",
            ),
        ).to_dict()
