import json
import os
import uuid
from typing import List, Dict, Any

SESSION_FILE = "sessions.json"

def load_sessions() -> Dict[str, Any]:
    if not os.path.exists(SESSION_FILE):
        return {}
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_sessions(sessions: Dict[str, Any]):
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2)

def create_session() -> str:
    sessions = load_sessions()
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "id": session_id,
        "messages": [],
        "active_files": [],
        "excluded_files": [],
        "accumulated_evidence": [],
        "context": {}
    }
    save_sessions(sessions)
    return session_id

def get_session(session_id: str) -> Dict[str, Any]:
    sessions = load_sessions()
    return sessions.get(session_id)

def add_message(session_id: str, role: str, content: str, tool_calls=None, evidence=None):
    sessions = load_sessions()
    if session_id not in sessions:
        return
    msg = {"role": role, "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if evidence:
        msg["evidence"] = evidence
        sessions[session_id]["accumulated_evidence"].extend(evidence)
    sessions[session_id]["messages"].append(msg)
    
    # Bounded context management
    if len(sessions[session_id]["messages"]) > 20:
        # Keep first 2 (system prompt + first query) and last 10
        sessions[session_id]["messages"] = sessions[session_id]["messages"][:2] + sessions[session_id]["messages"][-10:]
        
    save_sessions(sessions)

def update_files(session_id: str, add_files: List[str] = None, exclude_files: List[str] = None):
    sessions = load_sessions()
    if session_id not in sessions:
        return
    if add_files:
        for f in add_files:
            if f not in sessions[session_id]["active_files"]:
                sessions[session_id]["active_files"].append(f)
            if f in sessions[session_id]["excluded_files"]:
                sessions[session_id]["excluded_files"].remove(f)
    if exclude_files:
        for f in exclude_files:
            if f not in sessions[session_id]["excluded_files"]:
                sessions[session_id]["excluded_files"].append(f)
            if f in sessions[session_id]["active_files"]:
                sessions[session_id]["active_files"].remove(f)
    save_sessions(sessions)

