import os
import smtplib
from email.message import EmailMessage
import logging
import json

logger = logging.getLogger("EmailAlerts")

class EmailNotifier:
    """
    Sends the generated JSON report and risk assessment to a designated administrator.
    """
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.sender_email = os.getenv("SMTP_EMAIL", "your_email@gmail.com")
        self.sender_password = os.getenv("SMTP_PASSWORD", "")
        self.admin_email = os.getenv("ADMIN_EMAIL", "admin@yourcompany.com")
        
    def send_report(self, report_path: str):
        if not self.sender_password:
            logger.warning("SMTP_PASSWORD not set. Skipping email delivery.")
            return False
            
        try:
            with open(report_path, "r") as f:
                report_data = json.load(f)
                
            session_info = report_data.get("session_info", {})
            risk_info = report_data.get("risk_assessment", {})
            
            subject = f"[Optimus Alert] Session {session_info.get('session_id')} - Risk Level: {risk_info.get('level')}"
            
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.sender_email
            msg["To"] = self.admin_email
            
            body = f"""Optimus Identity & Integrity Report
-----------------------------------------
Session ID: {session_info.get('session_id')}
Candidate ID: {session_info.get('candidate_id')}
Status: {session_info.get('status')}

Integrity Score: {risk_info.get('score')}/100
Risk Level: {risk_info.get('level')}

Please find the detailed JSON session report attached for auditing.
"""
            msg.set_content(body)
            
            # Attach the JSON report
            with open(report_path, "rb") as f:
                report_bytes = f.read()
                msg.add_attachment(report_bytes, maintype="application", subtype="json", filename=os.path.basename(report_path))
                
            # Send Email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
                
            logger.info(f"Email report sent to {self.admin_email} successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to send email report: {e}")
            return False

if __name__ == "__main__":
    notifier = EmailNotifier()
    # print(notifier.send_report("./reports/session_xyz_report.json"))
