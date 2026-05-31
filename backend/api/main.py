"""
Optimus API – lightweight FastAPI health/session endpoint.
No WireGuard, no desktop, no Electron dependencies.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.session_manager import SessionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OptimusAPI")

app = FastAPI(title="Optimus Monitoring API")
session_manager = SessionManager()


class SessionCreateRequest(BaseModel):
    candidate_id: str


@app.post("/session/create")
async def create_session(request: SessionCreateRequest):
    sid = session_manager.start_session()
    return {"session_id": sid, "status": "active"}


@app.post("/session/{session_id}/end")
async def end_session(session_id: str):
    session_manager.end_session(session_id)
    return {"status": "ended", "session_id": session_id}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Optimus Monitoring API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
