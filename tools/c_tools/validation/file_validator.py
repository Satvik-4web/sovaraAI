"""
File Integrity & Hash Validator module.
Verifies file existence, size, MIME type format, and SHA-256 checksum hashes.
"""

import hashlib
import mimetypes
import time
from pathlib import Path
from typing import Dict, Any, Optional

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.file_ops.path_security import validate_workspace_path


def validate_file_integrity(
    file_path: str,
    expected_hash: Optional[str] = None,
    workspace_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates file existence, non-zero byte size, MIME format type, and SHA-256 hash checksum.

    Args:
        file_path: Target file path within workspace.
        expected_hash: Optional expected SHA-256 hash string for verification.
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
                message=f"File not found for integrity validation: '{file_path}'",
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
        stat = validated_path.stat()
        file_size = stat.st_size

        # Compute SHA-256 checksum
        hasher = hashlib.sha256()
        with open(validated_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        # Check hash match if expected_hash provided
        if expected_hash and sha256_hash.lower() != expected_hash.strip().lower():
            return ExecutionResult(
                success=False,
                execution_time=time.perf_counter() - start_time,
                error=ExecutionError(
                    code=ErrorCode.CHECKSUM_MISMATCH,
                    message=f"File hash mismatch! Expected: '{expected_hash}', Computed: '{sha256_hash}'.",
                ),
            ).to_dict()

        mime_type, encoding = mimetypes.guess_type(str(validated_path))
        exec_time = time.perf_counter() - start_time

        return ExecutionResult(
            success=True,
            result={
                "filename": validated_path.name,
                "size_bytes": file_size,
                "is_empty": file_size == 0,
                "sha256_hash": sha256_hash,
                "mime_type": mime_type or "application/octet-stream",
                "hash_verified": True if expected_hash else False,
            },
            execution_time=exec_time,
        ).to_dict()

    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.FILE_OPERATION_ERROR,
                message=f"Error validating file integrity for '{file_path}': {str(e)}",
            ),
        ).to_dict()
