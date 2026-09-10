"""
Unit tests for CSV and Excel Data Analysis tools.
"""

import tempfile
import shutil
import unittest
from pathlib import Path

from tools.c_tools.analysis.csv_analyzer import analyze_csv
from tools.c_tools.analysis.excel_analyzer import analyze_excel
from tools.c_tools.file_ops.file_manager import write_file_content
from tools.c_tools.schemas import ErrorCode


class TestCSVAndExcelAnalysis(unittest.TestCase):
    """Test suite for CSV and Excel data profiling."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sovara_test_analysis_")
        self.workspace_root = str(Path(self.temp_dir).resolve())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_csv_analysis_basic(self):
        """Test analyzing a standard CSV file."""
        csv_data = (
            "id,name,score,active\n"
            "1,Alice,95.5,true\n"
            "2,Bob,88.0,false\n"
            "3,Charlie,,true\n"
        )
        write_file_content("data.csv", csv_data, workspace_root=self.workspace_root)

        res = analyze_csv("data.csv", preview_rows=2, workspace_root=self.workspace_root)
        self.assertTrue(res["success"])

        data = res["result"]
        self.assertEqual(data["row_count"], 3)
        self.assertEqual(data["column_count"], 4)
        self.assertEqual(len(data["preview"]), 2)

        cols = {c["name"]: c for c in data["columns"]}
        self.assertEqual(cols["id"]["inferred_type"], "int")
        self.assertEqual(cols["score"]["null_count"], 1)

    def test_csv_custom_delimiter(self):
        """Test CSV with semicolon delimiter."""
        csv_data = "col1;col2\n100;ABC\n200;XYZ\n"
        write_file_content("semi.csv", csv_data, workspace_root=self.workspace_root)

        res = analyze_csv("semi.csv", workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["column_count"], 2)

    def test_csv_missing_file(self):
        """Verify FILE_NOT_FOUND handling in CSV analyzer."""
        res = analyze_csv("non_existent.csv", workspace_root=self.workspace_root)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], ErrorCode.FILE_NOT_FOUND.value)

    def test_excel_missing_openpyxl_or_file(self):
        """Verify Excel missing file error response."""
        res = analyze_excel("missing.xlsx", workspace_root=self.workspace_root)
        self.assertFalse(res["success"])
        self.assertIn(res["error"]["code"], [ErrorCode.FILE_NOT_FOUND.value, ErrorCode.INVALID_FILE_FORMAT.value])


if __name__ == "__main__":
    unittest.main()
