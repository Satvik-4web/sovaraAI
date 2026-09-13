import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from agents.session import create_session, get_session, update_files, load_sessions
from agents.chat_engine import stream_chat

chat_router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str
    active_files: Optional[List[str]] = None
    exclude_files: Optional[List[str]] = None

@chat_router.post("/api/chat/session")
async def start_session():
    session_id = create_session()
    return {"session_id": session_id}

@chat_router.get("/api/chat/session/{session_id}")
async def fetch_session(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@chat_router.post("/api/chat/message/{session_id}")
async def send_message(session_id: str, req: ChatMessageRequest):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    update_files(session_id, req.active_files, req.exclude_files)
    
    return StreamingResponse(
        stream_chat(session_id, req.message),
        media_type="text/event-stream"
    )

@chat_router.get("/api/chat/sessions")
async def fetch_sessions():
    sessions = load_sessions()
    res = []
    for sid, s in sessions.items():
        msgs = s.get("messages", [])
        user_msgs = [m["content"] for m in msgs if m["role"] == "user" and type(m["content"]) == str]
        title = user_msgs[0][:30] + "..." if user_msgs else "New Session"
        res.append({"id": sid, "title": title})
    res.reverse()
    return res
