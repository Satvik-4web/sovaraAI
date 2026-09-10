"""
Master test suite entrypoint for SOVARA Tools Subsystem.
Aggregates sandbox, file operations, data analysis, document generation, and validation test cases.
"""

import unittest
from tools.c_tools.tests.test_unit import TestUnitSchemasAndConfig, TestUnitExecutorValidationAndMocking, TestUnitToolRegistry
from tools.c_tools.tests.test_file_ops import TestFileOpsSecurityAndOperations
from tools.c_tools.tests.test_excel_csv import TestCSVAndExcelAnalysis
from tools.c_tools.tests.test_documents import TestDocumentGeneration
from tools.c_tools.tests.test_validation import TestOutputAndFileValidation
from tools.c_tools.tests.test_integration import TestDockerIntegrationAndSecurity, TestDockerGracefulFailure

if __name__ == "__main__":
    unittest.main()
