"""
Unit tests for Document Generation Subsystem.
Tests Word (.docx), PowerPoint (.pptx), Markdown (.md), and PDF report creation.
"""

import tempfile
import shutil
import unittest
from pathlib import Path

from tools.c_tools.documents.docx_generator import generate_docx
from tools.c_tools.documents.pptx_generator import generate_pptx
from tools.c_tools.documents.markdown_generator import generate_markdown
from tools.c_tools.documents.pdf_generator import generate_pdf_report
from tools.c_tools.schemas import ErrorCode


class TestDocumentGeneration(unittest.TestCase):
    """Test suite for document generation tools."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="sovara_test_docs_")
        self.workspace_root = str(Path(self.temp_dir).resolve())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_docx(self):
        """Test Word document generation."""
        sections = [
            {"heading": "Executive Summary", "content": "SOVARA initial findings."},
            {"heading": "Metrics", "bullet_points": ["Point A", "Point B"]},
            {
                "heading": "Data Table",
                "table": {
                    "headers": ["Col 1", "Col 2"],
                    "rows": [["A", "1"], ["B", "2"]],
                },
            },
        ]
        res = generate_docx("report.docx", "SOVARA Report", sections, workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["sections_count"], 3)
        self.assertTrue(Path(res["result"]["path"]).exists())

    def test_generate_pptx(self):
        """Test PowerPoint presentation generation."""
        slides = [
            {"title": "Overview", "bullet_points": ["Key Takeaway 1", "Key Takeaway 2"]},
            {"title": "Details", "content": "Full summary text."},
        ]
        res = generate_pptx("briefing.pptx", "SOVARA Briefing", slides, workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["slides_count"], 3)  # Title + 2 content slides
        self.assertTrue(Path(res["result"]["path"]).exists())

    def test_generate_markdown(self):
        """Test Markdown document generation with frontmatter."""
        res = generate_markdown(
            "summary.md",
            "Project Summary",
            "## Details\nSome content.",
            metadata={"author": "Antigravity", "date": "2026-09-10"},
            workspace_root=self.workspace_root,
        )
        self.assertTrue(res["success"])
        self.assertTrue(Path(res["result"]["path"]).exists())
        
        with open(res["result"]["path"], "r", encoding="utf-8") as f:
            text = f.read()
            self.assertIn("author: \"Antigravity\"", text)
            self.assertIn("# Project Summary", text)

    def test_generate_pdf_report(self):
        """Test PDF/HTML report generation."""
        res = generate_pdf_report("output.pdf", "Status Report", "All systems operational.", workspace_root=self.workspace_root)
        self.assertTrue(res["success"])
        self.assertTrue(Path(res["result"]["path"]).exists())

    def test_path_traversal_blocking(self):
        """Verify path traversal protection on document generation."""
        res = generate_markdown("../hacked.md", "Title", "Body", workspace_root=self.workspace_root)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], ErrorCode.PATH_TRAVERSAL_ATTEMPT.value)


if __name__ == "__main__":
    unittest.main()
