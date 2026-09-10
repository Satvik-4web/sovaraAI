"""
Unit tests for SOVARA Python Executor Subsystem.
Runs fast unit tests without requiring a live Docker daemon.
"""

import unittest
from unittest.mock import MagicMock

from tools.c_tools.config import SandboxConfig
from tools.c_tools.schemas import ExecutionResult, ExecutionError, ErrorCode
from tools.c_tools.sandbox.resource_limits import ResourceLimits
from tools.c_tools.sandbox.docker_runner import DockerRunner
from tools.c_tools.sandbox.python_executor import execute_python
from tools.c_tools.registry import ToolRegistry


class TestUnitSchemasAndConfig(unittest.TestCase):
    """Test schema transformations and configuration objects."""

    def test_success_schema_dict_formatting(self):
        result = ExecutionResult(
            success=True,
            stdout="6000\n",
            stderr="",
            result=6000,
            execution_time=0.123456,
        )
        data = result.to_dict()
        self.assertTrue(data["success"])
        self.assertEqual(data["stdout"], "6000\n")
        self.assertEqual(data["stderr"], "")
        self.assertEqual(data["result"], 6000)
        self.assertIn("execution_time", data)
        self.assertNotIn("error", data)

    def test_failure_schema_dict_formatting(self):
        err = ExecutionError(code=ErrorCode.SANDBOX_TIMEOUT, message="Execution timed out.")
        result = ExecutionResult(
            success=False,
            error=err,
        )
        data = result.to_dict()
        self.assertFalse(data["success"])
        self.assertNotIn("stdout", data)
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "SANDBOX_TIMEOUT")
        self.assertEqual(data["error"]["message"], "Execution timed out.")

    def test_resource_limits_validation(self):
        invalid_timeout = ResourceLimits(timeout=-1)
        with self.assertRaises(ValueError):
            invalid_timeout.validate()

        invalid_cpu = ResourceLimits(cpu_limit=0)
        with self.assertRaises(ValueError):
            invalid_cpu.validate()


class TestUnitExecutorValidationAndMocking(unittest.TestCase):
    """Test execute_python input validation and mock runner responses."""

    def test_empty_code_input(self):
        res = execute_python("")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "INVALID_INPUT")

    def test_non_string_code_input(self):
        res = execute_python(None)  # type: ignore
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "INVALID_INPUT")

    def test_mock_docker_unavailable(self):
        mock_runner = MagicMock(spec=DockerRunner)
        mock_runner.run.return_value = ExecutionResult(
            success=False,
            error=ExecutionError(
                code=ErrorCode.DOCKER_UNAVAILABLE,
                message="Docker daemon unreachable.",
            ),
        )

        res = execute_python("print('hello')", runner=mock_runner)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "DOCKER_UNAVAILABLE")

    def test_mock_successful_execution(self):
        mock_runner = MagicMock(spec=DockerRunner)
        mock_runner.run.return_value = ExecutionResult(
            success=True,
            stdout="6000\n",
            stderr="",
            result=6000,
            execution_time=0.05,
        )

        res = execute_python("print(125 * 48)", runner=mock_runner)
        self.assertTrue(res["success"])
        self.assertEqual(res["stdout"], "6000\n")


class TestUnitToolRegistry(unittest.TestCase):
    """Test tool registry functionality."""

    def test_registry_register_and_execute(self):
        registry = ToolRegistry()
        registry.register("execute_python", execute_python)

        self.assertIn("execute_python", registry.list_tools())
        res = registry.execute("execute_python", code="")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "INVALID_INPUT")

    def test_registry_unregistered_tool(self):
        registry = ToolRegistry()
        res = registry.execute("non_existent_tool")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
