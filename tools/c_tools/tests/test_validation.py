"""
Unit tests for Output and File Integrity Validation tools.
"""

import tempfile
import shutil
import hashlib
import unittest
from pathlib import Path

from tools.c_tools.validation.output_validator import validate_tool_output
from tools.c_tools.validation.file_validator import validate_file_integrity
from tools.c_tools.file_ops.file_manager import write_file_content
from tools.c_tools.schemas import ErrorCode


class TestOutputAndFileValidation(unittest.TestCase):
    """Test suite for output contract validation and file integrity checks."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sovara_test_val_")
        self.workspace_root = str(Path(self.temp_dir).resolve())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_valid_tool_output(self):
        """Test validation of a valid successful tool output payload."""
        valid_payload = {
            "success": True,
            "stdout": "6000\n",
            "stderr": "",
            "result": 6000,
            "execution_time": 0.05,
        }
        res = validate_tool_output(valid_payload)
        self.assertTrue(res["success"])
        self.assertTrue(res["result"]["is_valid"])

    def test_validate_valid_error_tool_output(self):
        """Test validation of a valid error tool output payload."""
        error_payload = {
            "success": False,
            "error": {
                "code": "SANDBOX_TIMEOUT",
                "message": "Execution timed out.",
            },
        }
        res = validate_tool_output(error_payload)
        self.assertTrue(res["success"])

    def test_validate_invalid_tool_output(self):
        """Test rejection of malformed tool output payloads."""
        invalid_payloads = [
            "not_a_dict",
            {"success": "not_a_bool"},
            {"success": True},  # Missing stdout, stderr, result, execution_time
            {"success": False, "error": "not_a_dict"},
        ]
        for payload in invalid_payloads:
            res = validate_tool_output(payload)  # type: ignore
            self.assertFalse(res["success"])
            self.assertEqual(res["error"]["code"], ErrorCode.VALIDATION_FAILED.value)

    def test_file_integrity_validation(self):
        """Test file integrity and SHA-256 hash checksum matching."""
        content = "Confidential Data Payload"
        write_file_content("data.bin", content, workspace_root=self.workspace_root)

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        res_valid = validate_file_integrity("data.bin", expected_hash=expected_hash, workspace_root=self.workspace_root)
        self.assertTrue(res_valid["success"])
        self.assertEqual(res_valid["result"]["sha256_hash"], expected_hash)

        # Mismatch test
        res_mismatch = validate_file_integrity("data.bin", expected_hash="0000000000000000000000000000000000000000000000000000000000000000", workspace_root=self.workspace_root)
        self.assertFalse(res_mismatch["success"])
        self.assertEqual(res_mismatch["error"]["code"], ErrorCode.CHECKSUM_MISMATCH.value)


if __name__ == "__main__":
    unittest.main()
