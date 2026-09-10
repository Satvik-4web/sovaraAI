"""
Unit tests for SOVARA File Operations Subsystem.
Tests path traversal safety, reading, writing, directory listing, and deletion.
"""

import os
import tempfile
import shutil
import unittest
from pathlib import Path

from tools.c_tools.file_ops.path_security import validate_workspace_path
from tools.c_tools.file_ops.file_manager import (
    read_file_content,
    write_file_content,
    list_workspace_directory,
    delete_workspace_file,
)
from tools.c_tools.schemas import ErrorCode


class TestFileOpsSecurityAndOperations(unittest.TestCase):
    """Test suite for workspace file operations and path security."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sovara_test_workspace_")
        self.workspace_root = str(Path(self.temp_dir).resolve())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_traversal_blocking(self):
        """Verify that path traversal attempts escaping the workspace are blocked."""
        bad_paths = [
            "../secret.txt",
            "../../etc/passwd",
            "C:\\Windows\\System32\\cmd.exe",
            "/etc/shadow",
            "subfolder/../../outside.txt",
        ]
        for p in bad_paths:
            with self.assertRaises(ValueError):
                validate_workspace_path(p, workspace_root=self.workspace_root)

    def test_write_and_read_file(self):
        """Test writing a file and reading its content back."""
        res_write = write_file_content(
            "sub/test.txt",
            "Hello SOVARA",
            workspace_root=self.workspace_root,
        )
        self.assertTrue(res_write["success"])

        res_read = read_file_content("sub/test.txt", workspace_root=self.workspace_root)
        self.assertTrue(res_read["success"])
        self.assertEqual(res_read["result"]["content"], "Hello SOVARA")
        self.assertFalse(res_read["result"]["truncated"])

    def test_overwrite_protection(self):
        """Verify overwrite protection when overwrite=False."""
        write_file_content("existing.txt", "V1", workspace_root=self.workspace_root)
        res_overwrite = write_file_content(
            "existing.txt", "V2", overwrite=False, workspace_root=self.workspace_root
        )
        self.assertFalse(res_overwrite["success"])
        self.assertEqual(res_overwrite["error"]["code"], ErrorCode.FILE_ALREADY_EXISTS.value)

    def test_read_non_existent_file(self):
        """Verify file not found error code."""
        res = read_file_content("missing.txt", workspace_root=self.workspace_root)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], ErrorCode.FILE_NOT_FOUND.value)

    def test_read_file_truncation(self):
        """Verify max_bytes reading limit."""
        large_content = "X" * 2000
        write_file_content("large.txt", large_content, workspace_root=self.workspace_root)

        res = read_file_content("large.txt", max_bytes=500, workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        self.assertEqual(len(res["result"]["content"]), 500)
        self.assertTrue(res["result"]["truncated"])

    def test_list_directory(self):
        """Test listing directory contents."""
        write_file_content("f1.txt", "1", workspace_root=self.workspace_root)
        write_file_content("sub/f2.txt", "2", workspace_root=self.workspace_root)

        res = list_workspace_directory(".", workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        items = [i["name"] for i in res["result"]["items"]]
        self.assertIn("f1.txt", items)
        self.assertIn("sub", items)

    def test_delete_file(self):
        """Test deleting a file."""
        write_file_content("to_del.txt", "bye", workspace_root=self.workspace_root)
        res_del = delete_workspace_file("to_del.txt", workspace_root=self.workspace_root)
        self.assertTrue(res_del["success"])

        res_read = read_file_content("to_del.txt", workspace_root=self.workspace_root)
        self.assertFalse(res_read["success"])


if __name__ == "__main__":
    unittest.main()
