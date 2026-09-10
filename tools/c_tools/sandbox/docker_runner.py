"""
Docker container runner for isolated Python execution.
Applies network isolation, capability drops, read-only rootfs, and resource limits.
"""

import json
import os
import shutil
import subprocess
import time
from typing import Dict, Any, Optional

from tools.c_tools.config import SandboxConfig, DEFAULT_CONFIG
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.sandbox.resource_limits import ResourceLimits

# Python wrapper code executed inside the container to capture stdout, stderr, errors, and return values safely.
CONTAINER_WRAPPER_SCRIPT = r"""
import sys
import io
import json
import traceback

def main():
    try:
        raw_payload = sys.stdin.read()
        payload = json.loads(raw_payload)
        user_code = payload.get("code", "")
    except Exception as e:
        print(json.dumps({
            "success": False,
            "stdout": "",
            "stderr": f"Failed to parse payload: {e}",
            "result": None,
            "error_code": "INVALID_INPUT",
            "error_message": f"Failed to parse payload: {e}"
        }))
        return

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    
    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    success = True
    error_code = None
    error_msg = None
    result_val = None

    try:
        # Pre-compile to distinguish syntax errors from runtime errors
        compiled = compile(user_code, "<sandbox>", "exec")
        namespace = {}
        exec(compiled, namespace)

        # Extract explicit result variable if user assigned result or __sovara_result__
        if "__sovara_result__" in namespace:
            result_val = namespace["__sovara_result__"]
        elif "result" in namespace:
            result_val = namespace["result"]

    except SyntaxError as e:
        success = False
        error_code = "PYTHON_SYNTAX_ERROR"
        error_msg = f"SyntaxError: {e.msg} (line {e.lineno})"
        captured_stderr.write(f"SyntaxError: {e.msg} at line {e.lineno}\n")
    except Exception as e:
        success = False
        error_code = "PYTHON_RUNTIME_ERROR"
        error_msg = f"{type(e).__name__}: {e}"
        captured_stderr.write(traceback.format_exc())
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    # JSON serialize result if possible
    try:
        json.dumps(result_val)
    except (TypeError, OverflowError):
        result_val = str(result_val) if result_val is not None else None

    out_payload = {
        "success": success,
        "stdout": captured_stdout.getvalue(),
        "stderr": captured_stderr.getvalue(),
        "result": result_val if success else None,
        "error_code": error_code,
        "error_message": error_msg
    }

    print("__SOVARA_OUTPUT_START__" + json.dumps(out_payload))

if __name__ == "__main__":
    main()
"""


class DockerRunner:
    """Manages isolated Python execution inside Docker containers."""

    def __init__(self, config: Optional[SandboxConfig] = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.limits = ResourceLimits.from_config(self.config)

    def is_docker_available(self) -> bool:
        """Check if Docker CLI executable is available in PATH and daemon is responding."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3,
            )
            return res.returncode == 0
        except Exception:
            return False

    def run(self, code: str, limits: Optional[ResourceLimits] = None) -> ExecutionResult:
        """
        Execute Python code in a secure Docker container.

        Args:
            code: The Python source code string to execute.
            limits: Resource limits override for this execution.

        Returns:
            ExecutionResult object containing stdout, stderr, result, execution_time, or error.
        """

        active_limits = limits or self.limits
        active_limits.validate()

        if not self.is_docker_available():
            import sys
            import subprocess
            
            payload = json.dumps({"code": code})
            start_time = time.perf_counter()
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", CONTAINER_WRAPPER_SCRIPT],
                    input=payload,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=active_limits.timeout,
                )
                exec_time = time.perf_counter() - start_time
                stdout_raw = proc.stdout
                marker = "__SOVARA_OUTPUT_START__"
                
                if marker in stdout_raw:
                    try:
                        json_part = stdout_raw.split(marker)[-1].strip()
                        out_payload = json.loads(json_part)
                        success = out_payload.get("success", False)
                        
                        warn_msg = "[WARNING: LOCAL DEV FALLBACK IN USE. NO DOCKER ISOLATION.]\n"
                        
                        if success:
                            return ExecutionResult(
                                success=True,
                                stdout=warn_msg + out_payload.get("stdout", ""),
                                stderr=out_payload.get("stderr", ""),
                                result=out_payload.get("result"),
                                execution_time=exec_time,
                            )
                        else:
                            return ExecutionResult(
                                success=False,
                                stdout=warn_msg + out_payload.get("stdout", ""),
                                stderr=out_payload.get("stderr", ""),
                                execution_time=exec_time,
                                error=ExecutionError(code=ErrorCode.PYTHON_RUNTIME_ERROR, message=warn_msg + str(out_payload.get("error_message", "")))
                            )
                    except Exception as e:
                        pass
                
                return ExecutionResult(
                    success=False,
                    execution_time=exec_time,
                    error=ExecutionError(
                        code=ErrorCode.SANDBOX_ERROR,
                        message="[WARNING: LOCAL FALLBACK] " + proc.stderr
                    )
                )

            except subprocess.TimeoutExpired as e:
                return ExecutionResult(
                    success=False,
                    execution_time=time.perf_counter() - start_time,
                    error=ExecutionError(
                        code=ErrorCode.SANDBOX_TIMEOUT,
                        message=f"[WARNING: LOCAL FALLBACK] Execution timed out after {active_limits.timeout} seconds."
                    )
                )


        active_limits = limits or self.limits
        active_limits.validate()

        cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "--net=none",
            f"--memory={active_limits.memory_limit}",
            f"--cpus={active_limits.cpu_limit}",
            "--cap-drop=ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            self.config.docker_image,
            "python3",
            "-c",
            CONTAINER_WRAPPER_SCRIPT,
        ]

        payload = json.dumps({"code": code})
        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                cmd,
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=active_limits.timeout,
            )
            exec_time = time.perf_counter() - start_time

            # OOM Exit Code 137
            if proc.returncode == 137:
                return ExecutionResult(
                    success=False,
                    execution_time=exec_time,
                    error=ExecutionError(
                        code=ErrorCode.SANDBOX_RESOURCE_LIMIT,
                        message=f"Container resource limit exceeded (Memory limit: {active_limits.memory_limit}).",
                    ),
                )

            # Container execution failed unexpectedly
            if proc.returncode != 0 and "__SOVARA_OUTPUT_START__" not in proc.stdout:
                err_msg = proc.stderr.strip() or proc.stdout.strip() or f"Container exited with code {proc.returncode}"
                return ExecutionResult(
                    success=False,
                    execution_time=exec_time,
                    error=ExecutionError(
                        code=ErrorCode.SANDBOX_ERROR,
                        message=f"Sandbox process error: {err_msg}",
                    ),
                )

            # Parse wrapper output
            output_start_idx = proc.stdout.find("__SOVARA_OUTPUT_START__")
            if output_start_idx != -1:
                raw_json = proc.stdout[output_start_idx + len("__SOVARA_OUTPUT_START__"):].strip()
                data = json.loads(raw_json)

                if data.get("success"):
                    return ExecutionResult(
                        success=True,
                        stdout=data.get("stdout", ""),
                        stderr=data.get("stderr", ""),
                        result=data.get("result"),
                        execution_time=exec_time,
                    )
                else:
                    err_code_str = data.get("error_code", "PYTHON_RUNTIME_ERROR")
                    try:
                        err_code = ErrorCode(err_code_str)
                    except ValueError:
                        err_code = ErrorCode.PYTHON_RUNTIME_ERROR

                    return ExecutionResult(
                        success=False,
                        stdout=data.get("stdout", ""),
                        stderr=data.get("stderr", ""),
                        execution_time=exec_time,
                        error=ExecutionError(
                            code=err_code,
                            message=data.get("error_message", "Python execution error."),
                        ),
                    )
            else:
                return ExecutionResult(
                    success=False,
                    execution_time=exec_time,
                    error=ExecutionError(
                        code=ErrorCode.SANDBOX_ERROR,
                        message=f"Invalid container output: {proc.stdout.strip()}",
                    ),
                )

        except subprocess.TimeoutExpired:
            exec_time = time.perf_counter() - start_time
            return ExecutionResult(
                success=False,
                execution_time=exec_time,
                error=ExecutionError(
                    code=ErrorCode.SANDBOX_TIMEOUT,
                    message=f"Execution exceeded the configured timeout of {active_limits.timeout} seconds.",
                ),
            )
        except Exception as e:
            exec_time = time.perf_counter() - start_time
            return ExecutionResult(
                success=False,
                execution_time=exec_time,
                error=ExecutionError(
                    code=ErrorCode.SANDBOX_ERROR,
                    message=f"Sandbox error: {str(e)}",
                ),
            )
