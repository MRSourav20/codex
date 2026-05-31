import os
import json
import logging
from datetime import datetime
from backend.session_manager import SessionManager
from backend.dns_monitor.dns_logger import DNSLogger
from backend.risk_engine import RiskEngine

logger = logging.getLogger("ReportGenerator")

class ReportGenerator:
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.session_manager = SessionManager()
        self.dns_logger = DNSLogger()
        self.risk_engine = RiskEngine()

    def generate_session_report(self, session_id: str) -> str:
        """
        Generates a comprehensive JSON report for the session and updates the DB.
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.error(f"Cannot generate report, session {session_id} not found.")
            return ""
            
        candidate_id = session[1]
        client_ip = session[4]
        
        # Risk Evaluation
        eval_result = self.risk_engine.evaluate_session(session_id)
        
        # Domains
        import sqlite3
        conn = sqlite3.connect(self.dns_logger.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, domain, query_type, category, confidence, source FROM dns_queries WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        domain_rows = cursor.fetchall()
        domains = []
        for r in domain_rows:
            domains.append({
                "timestamp": r[0],
                "domain": r[1],
                "type": r[2],
                "category": r[3],
                "confidence": r[4],
                "source": r[5]
            })
            
        # Events
        events = self.dns_logger.get_suspicious_events(limit=1000, session_id=session_id)
        conn.close()

        report_data = {
            "session_info": {
                "session_id": session_id,
                "candidate_id": candidate_id,
                "client_ip": client_ip,
                "created_at": session[6],
                "ended_at": session[7] if session[7] else datetime.now().isoformat(),
                "status": session[5]
            },
            "risk_assessment": eval_result,
            "events_summary": events,
            "domain_log": domains
        }
        
        report_filename = f"session_{session_id}_report.json"
        report_path = os.path.join(self.output_dir, report_filename)
        
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=4)
            
        logger.info(f"Report generated: {report_path}")
        
        # Update SessionManager
        self.session_manager.update_report_path(session_id, report_path)
        
        return report_path
