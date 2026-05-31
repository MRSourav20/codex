import sqlite3
import uuid
import os
from datetime import datetime
import session_tunnel

DB_PATH = "sessions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            candidate_id TEXT,
            client_pubkey TEXT,
            client_privkey TEXT,
            client_ip TEXT,
            status TEXT,
            created_at TIMESTAMP,
            ended_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def create_session(candidate_id):
    session_id = str(uuid.uuid4())
    client_privkey, client_pubkey = session_tunnel.generate_key_pair()
    
    # Simple IP allocation logic for MVP (starts from 10.0.0.2)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM sessions")
    count = cursor.fetchone()[0]
    client_ip = f"10.0.0.{count + 2}"
    
    cursor.execute("""
        INSERT INTO sessions (session_id, candidate_id, client_pubkey, client_privkey, client_ip, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, candidate_id, client_pubkey, client_privkey, client_ip, "active", datetime.now()))
    
    conn.commit()
    conn.close()
    
    # In a real EC2 environment, we would call session_tunnel.add_peer here
    # but for local testing we will just return the data.
    return {
        "session_id": session_id,
        "client_pubkey": client_pubkey,
        "client_privkey": client_privkey,
        "client_ip": client_ip,
        "status": "active"
    }

def end_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT client_pubkey FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    if row:
        client_pubkey = row[0]
        # In real EC2: session_tunnel.remove_peer("wg0", client_pubkey)
        
        cursor.execute("""
            UPDATE sessions SET status = ?, ended_at = ? WHERE session_id = ?
        """, ("ended", datetime.now(), session_id))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# Initialize on import
init_db()
