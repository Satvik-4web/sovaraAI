import os
import shutil
import pytest
from multimodal.adapter import MultimodalAdapter
from tools.c_tools.analysis.excel_analyzer import analyze_excel
from fastapi.testclient import TestClient
from api_server import app, tasks_db, files_db

client = TestClient(app)

def test_pdf_upload_and_extract():
    task_id = "test-pdf-123"
    tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}
    files_db[task_id] = []
    
    with open("demo/inspection_report.pdf", "rb") as f:
        response = client.post(f"/api/tasks/{task_id}/files", files={"file": ("inspection_report.pdf", f, "application/pdf")})
    
    assert response.status_code == 200
    file_path = response.json()["path"]
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0
    
    # Test text extraction
    res = MultimodalAdapter.extract_text(file_path)
    assert res["success"] is True
    assert len(res["text"]) > 0

def test_pid_upload_and_analyze():
    task_id = "test-pid-123"
    tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}
    files_db[task_id] = []
    
    with open("demo/pump_pid.png", "rb") as f:
        response = client.post(f"/api/tasks/{task_id}/files", files={"file": ("pump_pid.png", f, "image/png")})
    
    assert response.status_code == 200
    file_path = response.json()["path"]
    assert os.path.exists(file_path)
    
    res = MultimodalAdapter.analyze_pid(file_path)
    assert "uncertainties" in res

def test_xlsx_upload_and_analyze():
    task_id = "test-xlsx-123"
    tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}
    files_db[task_id] = []
    
    with open("demo/pump_inspection.xlsx", "rb") as f:
        response = client.post(f"/api/tasks/{task_id}/files", files={"file": ("pump_inspection.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    
    assert response.status_code == 200
    file_path = response.json()["path"]
    assert os.path.exists(file_path)
    
    res = analyze_excel(file_path=file_path)
    assert res["status"] != "error"

def test_sop_retrieval():
    from Rag.search import search_knowledge
    chunks = search_knowledge("maintenance procedure", limit=3)
    # The actual qdrant DB might or might not have it, but we can verify no exception is thrown
    assert isinstance(chunks, list)

def test_cross_modal_hero_task():
    task_id = "test-hero-123"
    tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}
    
    files = ["demo/pump_pid.png", "demo/inspection_report.pdf", "demo/pump_inspection.xlsx"]
    for f_path in files:
        with open(f_path, "rb") as f:
            response = client.post(f"/api/tasks/{task_id}/files", files={"file": (os.path.basename(f_path), f, "application/octet-stream")})
            assert response.status_code == 200
    
    query = "Analyze P-101 using the provided files. Prepare an approval note."
    # We won't trigger the background thread here natively in pytest to avoid hangs,
    # but we can call run_sovara_task directly
    from main import run_sovara_task
    input_files = files_db.get(task_id, [])
    res = run_sovara_task(query, files=input_files)
    assert res.get("success") is True
    assert res.get("risk") is not None
