"""
Tool Output Contract Validator module.
Ensures tool execution responses conform strictly to SOVARA schema specifications.
"""

import time
from typing import Dict, Any, List

from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode


def validate_tool_output(output_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a tool execution response dictionary against the SOVARA API contract.

    Contract Rules:
    - Must be a dictionary.
    - Must contain 'success' key (boolean).
    - If success == True: must contain 'stdout' (str), 'stderr' (str), 'result' (Any), 'execution_time' (numeric).
    - If success == False: must contain 'error' (dict) with 'code' and 'message' keys.

    Args:
        output_dict: Tool response payload to validate.

    Returns:
        Structured ExecutionResult dictionary indicating validation pass/fail.
    """
    start_time = time.perf_counter()
    issues: List[str] = []

    if not isinstance(output_dict, dict):
        return ExecutionResult(
            success=False,
            execution_time=time.perf_counter() - start_time,
            error=ExecutionError(
                code=ErrorCode.VALIDATION_FAILED,
                message="Tool output payload must be a dictionary.",
            ),
        ).to_dict()

    if "success" not in output_dict or not isinstance(output_dict["success"], bool):
        issues.append("Missing or non-boolean 'success' field.")

    is_success = output_dict.get("success")

    if is_success is True:
        if "stdout" not in output_dict or not isinstance(output_dict["stdout"], str):
            issues.append("Successful tool output missing string field 'stdout'.")
        if "stderr" not in output_dict or not isinstance(output_dict["stderr"], str):
            issues.append("Successful tool output missing string field 'stderr'.")
        if "result" not in output_dict:
            issues.append("Successful tool output missing field 'result'.")
        if "execution_time" not in output_dict or not isinstance(output_dict["execution_time"], (int, float)):
            issues.append("Successful tool output missing numeric field 'execution_time'.")

    elif is_success is False:
        if "error" not in output_dict or not isinstance(output_dict["error"], dict):
            issues.append("Failed tool output missing dictionary field 'error'.")
        else:
            err = output_dict["error"]
            if "code" not in err or not isinstance(err["code"], str):
                issues.append("Error dictionary missing string field 'code'.")
            if "message" not in err or not isinstance(err["message"], str):
                issues.append("Error dictionary missing string field 'message'.")

    exec_time = time.perf_counter() - start_time

    if issues:
        return ExecutionResult(
            success=False,
            execution_time=exec_time,
            error=ExecutionError(
                code=ErrorCode.VALIDATION_FAILED,
                message=f"Output validation failed: {'; '.join(issues)}",
            ),
        ).to_dict()

    return ExecutionResult(
        success=True,
        result={
            "is_valid": True,
            "validated_keys": list(output_dict.keys()),
        },
        execution_time=exec_time,
    ).to_dict()
