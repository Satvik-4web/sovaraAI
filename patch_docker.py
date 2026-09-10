import re

with open('tools/c_tools/sandbox/docker_runner.py', 'r', encoding='utf-8') as f:
    content = f.read()

fallback = '''
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
                        
                        warn_msg = "[WARNING: LOCAL DEV FALLBACK IN USE. NO DOCKER ISOLATION.]\\n"
                        
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
'''

old_check = '''        if not self.is_docker_available():
            return ExecutionResult(
                success=False,
                error=ExecutionError(
                    code=ErrorCode.DOCKER_UNAVAILABLE,
                    message="Docker is not available or the Docker daemon is not running.",
                ),
            )'''

content = content.replace(old_check, fallback)

with open('tools/c_tools/sandbox/docker_runner.py', 'w', encoding='utf-8') as f:
    f.write(content)
