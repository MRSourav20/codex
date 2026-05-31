"""
Optimus Session Manager – tracks monitoring session lifecycle.
No WireGuard. No client keys. Pure session metadata.
"""
import sqlite3
import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "sessions.db")


class SessionManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id    TEXT PRIMARY KEY,
                started_at    TEXT NOT NULL,
                ended_at      TEXT,
                status        TEXT DEFAULT 'active',
                total_packets INTEGER DEFAULT 0,
                unique_domains INTEGER DEFAULT 0,
                risk_score    REAL DEFAULT 0.0,
                report_json   TEXT,
                report_html   TEXT,
                report_txt    TEXT
            )
        """)
        conn.commit()
        conn.close()

    # ------------------------------------------------------------------ #
    def start_session(self) -> str:
        session_id = str(uuid.uuid4())[:8].upper()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO sessions (session_id, started_at, status) VALUES (?, ?, 'active')",
            (session_id, datetime.now().isoformat())

        )
        conn.commit()
        conn.close()
        return session_id

    def end_session(self, session_id: str, stats: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE sessions SET
                ended_at = ?,
                status = 'ended',
                total_packets = ?,
                unique_domains = ?,
                risk_score = ?
            WHERE session_id = ?
        """, (
            datetime.now().isoformat(),
            stats.get("total_packets", 0),
            stats.get("unique_domains", 0),
            stats.get("risk_score", 0.0),
            session_id
        ))
        conn.commit()
        conn.close()

    def save_report_paths(self, session_id: str, json_path: str, html_path: str, txt_path: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE sessions SET report_json=?, report_html=?, report_txt=? WHERE session_id=?",
            (json_path, html_path, txt_path, session_id)
        )
        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> Optional[tuple]:
        conn = sqlite3.connect(self.db_path)
        row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        conn.close()
        return row

    def get_all_sessions(self):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT * FROM sessions ORDER BY started_at DESC").fetchall()
        conn.close()
        return rows
