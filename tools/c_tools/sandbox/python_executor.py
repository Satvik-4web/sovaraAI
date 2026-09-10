"""
Public entrypoint for secure Python code execution in SOVARA.
"""

from typing import Dict, Any, Optional

from tools.c_tools.config import SandboxConfig, DEFAULT_CONFIG
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.sandbox.resource_limits import ResourceLimits
from tools.c_tools.sandbox.docker_runner import DockerRunner


def execute_python(
    code: str,
    timeout: Optional[int] = None,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[float] = None,
    config: Optional[SandboxConfig] = None,
    runner: Optional[DockerRunner] = None,
) -> Dict[str, Any]:
    """
    Executes Python code safely inside an isolated Docker sandbox.

    Args:
        code: Python source code string to execute.
        timeout: Optional timeout override in seconds.
        memory_limit: Optional memory limit override (e.g. '256m', '512m').
        cpu_limit: Optional CPU core limit override (e.g. 0.5, 1.0).
        config: Optional custom SandboxConfig object.
        runner: Optional DockerRunner instance (used for dependency injection / mocking in tests).

    Returns:
        Structured dictionary adhering strictly to the SOVARA tool response contract.
    """
    # 1. Validate input
    if not isinstance(code, str) or not code.strip():
        return ExecutionResult(
            success=False,
            error=ExecutionError(
                code=ErrorCode.INVALID_INPUT,
                message="Code input must be a non-empty string.",
            ),
        ).to_dict()

    # 2. Resolve configuration & resource limits
    base_config = config or DEFAULT_CONFIG
    effective_timeout = timeout if timeout is not None else base_config.timeout
    effective_memory = memory_limit if memory_limit is not None else base_config.memory_limit
    effective_cpu = cpu_limit if cpu_limit is not None else base_config.cpu_limit

    try:
        limits = ResourceLimits(
            timeout=effective_timeout,
            memory_limit=effective_memory,
            cpu_limit=effective_cpu,
        )
        limits.validate()
    except ValueError as e:
        return ExecutionResult(
            success=False,
            error=ExecutionError(
                code=ErrorCode.INVALID_INPUT,
                message=f"Invalid resource limits configuration: {e}",
            ),
        ).to_dict()

    # 3. Instantiate and run Docker execution runner
    docker_runner = runner or DockerRunner(config=base_config)
    result = docker_runner.run(code=code, limits=limits)

    # 4. Format structured dictionary response
    return result.to_dict()
