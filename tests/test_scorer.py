import pytest
from datasets.benchmark.scoring import check_evidence

def test_valid_rag_evidence():
    actual = {"evidence": [{"source": "pump_manual.txt"}]}
    assert check_evidence([{"source": "pump_manual.txt"}], actual) is True

def test_invalid_rag_source():
    actual = {"evidence": [{"source": "wrong_manual.txt"}]}
    assert check_evidence([{"source": "pump_manual.txt"}], actual) is False

def test_valid_excel_evidence():
    actual = {"deliverables": [{"tool": "analyze_excel", "result": {"result": {"file_name": "pump_inspection.xlsx"}}}]}
    assert check_evidence([{"source": "pump_inspection.xlsx"}], actual) is True

def test_invalid_excel_evidence():
    actual = {"deliverables": [{"tool": "analyze_excel", "result": {"result": {"file_name": "wrong_file.xlsx"}}}]}
    assert check_evidence([{"source": "pump_inspection.xlsx"}], actual) is False

def test_unsupported_answer_fails():
    # To test actual scoring logic, we need to import or test the main logic. 
    # For now, we focus on the evidence function which is the core typed schema.
    pass

