"""
Schemas and data structures for SOVARA tool results and structured errors.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional, Dict


class ErrorCode(str, Enum):
    """Structured error codes for sandbox execution, file operations, analysis, and document/validation failures."""

    # Execution & Sandbox Errors
    INVALID_INPUT = "INVALID_INPUT"
    DOCKER_UNAVAILABLE = "DOCKER_UNAVAILABLE"
    SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT"
    SANDBOX_RESOURCE_LIMIT = "SANDBOX_RESOURCE_LIMIT"
    PYTHON_SYNTAX_ERROR = "PYTHON_SYNTAX_ERROR"
    PYTHON_RUNTIME_ERROR = "PYTHON_RUNTIME_ERROR"
    SANDBOX_ERROR = "SANDBOX_ERROR"

    # File Operations & Path Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PATH_TRAVERSAL_ATTEMPT = "PATH_TRAVERSAL_ATTEMPT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_ALREADY_EXISTS = "FILE_ALREADY_EXISTS"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"
    FILE_OPERATION_ERROR = "FILE_OPERATION_ERROR"

    # Document Generation & Validation Errors
    DOCUMENT_GENERATION_ERROR = "DOCUMENT_GENERATION_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    CHECKSUM_MISMATCH = "CHECKSUM_MISMATCH"


@dataclass
class ExecutionError:
    """Structured error object containing error code and human-readable message."""

    code: ErrorCode
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert error instance to JSON-serializable dictionary."""
        return {
            "code": self.code.value if isinstance(self.code, ErrorCode) else str(self.code),
            "message": self.message,
        }


@dataclass
class ExecutionResult:
    """Structured output result for code execution or tool invocations."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    result: Any = None
    execution_time: float = 0.0
    error: Optional[ExecutionError] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result instance to the required SOVARA API contract structure.
        When success is True: returns success, stdout, stderr, result, execution_time.
        When success is False: returns success, error object.
        """
        if self.success:
            return {
                "success": True,
                "stdout": self.stdout,
                "stderr": self.stderr,
                "result": self.result,
                "execution_time": round(self.execution_time, 4),
            }
        else:
            err_dict = self.error.to_dict() if self.error else {
                "code": ErrorCode.SANDBOX_ERROR.value,
                "message": "Unknown error.",
            }
            return {
                "success": False,
                "error": err_dict,
            }
