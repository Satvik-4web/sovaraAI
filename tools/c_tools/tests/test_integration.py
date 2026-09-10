"""
Integration & Security isolation tests for SOVARA Docker Python Sandbox.
Tests require Docker daemon to be running; skipped automatically if Docker is unavailable.
"""

import unittest
from tools.c_tools.sandbox.docker_runner import DockerRunner
from tools.c_tools.sandbox.python_executor import execute_python
from tools.c_tools.schemas import ErrorCode


class TestDockerIntegrationAndSecurity(unittest.TestCase):
    """Integration test suite executing inside live Docker containers."""

    @classmethod
    def setUpClass(cls):
        cls.runner = DockerRunner()
        cls.docker_available = cls.runner.is_docker_available()

    def setUp(self):
        if not self.docker_available:
            self.skipTest("Docker is not available or daemon is not running.")

    def test_1_basic_arithmetic(self):
        """Test basic arithmetic expression execution."""
        res = execute_python("print(125 * 48)")
        self.assertTrue(res["success"], f"Execution failed: {res}")
        self.assertEqual(res["stdout"].strip(), "6000")
        self.assertEqual(res["stderr"], "")

    def test_2_python_calculation(self):
        """Test standard library math functions."""
        code = "import math\nprint(math.sqrt(144))"
        res = execute_python(code)
        self.assertTrue(res["success"])
        self.assertEqual(res["stdout"].strip(), "12.0")

    def test_3_pandas_calculation(self):
        """Test pandas operations if pandas is installed in container."""
        code = (
            "import pandas as pd\n"
            "df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})\n"
            "print(df['a'].sum())"
        )
        res = execute_python(code)
        if res["success"]:
            self.assertEqual(res["stdout"].strip(), "3")

    def test_4_syntax_error(self):
        """Test handling of Python syntax errors."""
        res = execute_python("def broken_function(")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "PYTHON_SYNTAX_ERROR")

    def test_5_runtime_error(self):
        """Test handling of Python runtime exceptions."""
        res = execute_python("x = 10 / 0")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "PYTHON_RUNTIME_ERROR")

    def test_6_timeout(self):
        """Test enforcement of execution timeout limits."""
        res = execute_python("while True: pass", timeout=2)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "SANDBOX_TIMEOUT")

    def test_7_file_isolation(self):
        """Verify host file system access is denied inside container."""
        code = (
            "try:\n"
            "    with open('/etc/passwd', 'r') as f:\n"
            "        print(f.read())\n"
            "except Exception as e:\n"
            "    print('ACCESS_DENIED')\n"
        )
        res = execute_python(code)
        self.assertTrue(res["success"])
        self.assertNotIn("root:", res["stdout"])

    def test_8_network_isolation(self):
        """Verify host network access is disabled inside container."""
        code = (
            "import socket\n"
            "try:\n"
            "    s = socket.create_connection(('8.8.8.8', 53), timeout=2)\n"
            "    print('CONNECTED')\n"
            "except Exception as e:\n"
            "    print('NETWORK_DISABLED')\n"
        )
        res = execute_python(code)
        self.assertTrue(res["success"])
        self.assertEqual(res["stdout"].strip(), "NETWORK_DISABLED")

    def test_9_resource_limits(self):
        """Verify memory limits (OOM handling)."""
        code = "a = 'x' * (500 * 1024 * 1024)"  # Attempt to allocate 500MB with 64m limit
        res = execute_python(code, memory_limit="64m")
        self.assertFalse(res["success"])
        self.assertIn(res["error"]["code"], ["SANDBOX_RESOURCE_LIMIT", "PYTHON_RUNTIME_ERROR"])


class TestDockerGracefulFailure(unittest.TestCase):
    """Test graceful error handling when Docker is unavailable."""

    def test_docker_unavailable_handling(self):
        runner = DockerRunner()
        if not runner.is_docker_available():
            res = execute_python("print('test')")
            self.assertFalse(res["success"])
            self.assertEqual(res["error"]["code"], ErrorCode.DOCKER_UNAVAILABLE.value)


if __name__ == "__main__":
    unittest.main()
