from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uuid
import os
import shutil
from main import run_sovara_task

app = FastAPI(title="SOVARA API")

tasks_db = {}
files_db = {}

class TaskRunRequest(BaseModel):
    query: str
    options: Optional[Dict[str, Any]] = None

@app.post("/api/tasks")
async def create_task():
    task_id = f"SOV-{uuid.uuid4().hex[:8].upper()}"
    tasks_db[task_id] = {"id": task_id, "status": "CREATED", "events": []}
    files_db[task_id] = []
    return {"task_id": task_id}

@app.post("/api/tasks/{task_id}/files")
async def upload_file(task_id: str, file: UploadFile = File(...)):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
        
    os.makedirs(f"uploads/{task_id}", exist_ok=True)
    file_path = f"uploads/{task_id}/{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    files_db[task_id].append(file_path)
    return {"message": "File uploaded", "path": file_path}

@app.post("/api/tasks/{task_id}/run")
async def run_task(task_id: str, request: TaskRunRequest, background_tasks: BackgroundTasks):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
        
    tasks_db[task_id]["status"] = "RUNNING"
    tasks_db[task_id]["events"].append({"event": "TASK_STARTED", "status": "running"})
    
    def _run():
        res = run_sovara_task(request.query, files=files_db.get(task_id, []))
        tasks_db[task_id]["result"] = res
        tasks_db[task_id]["status"] = res.get("status", "COMPLETED")
        for event in res.get("execution", {}).get("steps", []):
            tasks_db[task_id]["events"].append({"event": event, "status": "completed"})
            
    background_tasks.add_task(_run)
    return {"message": "Task started", "task_id": task_id}

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.get("/api/tasks/{task_id}/events")
async def get_task_events(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"events": tasks_db[task_id].get("events", [])}

@app.get("/api/tasks/{task_id}/outputs")
async def get_task_outputs(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    res = tasks_db[task_id].get("result", {})
    return {"outputs": res.get("outputs", [])}
