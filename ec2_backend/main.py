from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import session_manager
import os

app = FastAPI(title="Coadex 2.0 Identity Gateway")

class SessionStartRequest(BaseModel):
    candidate_id: str

class EventReport(BaseModel):
    session_id: str
    event_type: str
    details: dict

@app.post("/session/start")
async def start_session(request: SessionStartRequest):
    session_data = session_manager.create_session(request.candidate_id)
    
    # Constructing the WireGuard config for the client
    # These would normally come from an environment config or server state
    server_pubkey = os.getenv("WG_SERVER_PUBKEY", "SERVER_PUBKEY_PLACEHOLDER")
    server_endpoint = os.getenv("WG_SERVER_IP", "3.235.42.166")
    
    wg_config = f"""[Interface]
PrivateKey = {session_data['client_privkey']}
Address = {session_data['client_ip']}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pubkey}
Endpoint = {server_endpoint}:51820
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return {
        "session_id": session_data["session_id"],
        "wg_config": wg_config,
        "status": "active"
    }

@app.post("/session/end/{session_id}")
async def end_session(session_id: str):
    success = session_manager.end_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "ended"}

@app.post("/events/{session_id}")
async def receive_event(session_id: str, event: EventReport):
    # This will be expanded in Chunk 6 for the anomaly engine
    print(f"Received event from {session_id}: {event.event_type}")
    return {"status": "received"}

@app.get("/report/{session_id}")
async def get_report(session_id: str):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session[0],
        "candidate_id": session[1],
        "status": session[5],
        "created_at": session[6],
        "ended_at": session[7]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
