"""
Optimus SMTP Sender – delivers session reports by email.

Required .env variables (all optional – skips silently if missing):
    SMTP_HOST       smtp.gmail.com
    SMTP_PORT       587
    SMTP_USER       your@gmail.com
    SMTP_PASS       app-password
    SMTP_TO         recipient@example.com
"""
import os
import smtplib
import logging
from email.message import EmailMessage
from typing import Dict

logger = logging.getLogger("SmtpSender")


class SmtpSender:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.pwd  = os.getenv("SMTP_PASS", "")
        self.to   = os.getenv("SMTP_TO", "")
        self.enabled = bool(self.host and self.user and self.pwd and self.to)
        if not self.enabled:
            logger.info("SMTP not configured – email delivery disabled.")

    def send(self, session_id: str, paths: Dict[str, str]) -> bool:
        if not self.enabled:
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = f"[Optimus] Session {session_id} Report"
            msg["From"]    = self.user
            msg["To"]      = self.to

            # Read txt for body
            txt_body = ""
            if paths.get("txt") and os.path.exists(paths["txt"]):
                with open(paths["txt"]) as f:
                    txt_body = f.read()
            msg.set_content(txt_body or f"Optimus session {session_id} completed.")

            # HTML alternative
            if paths.get("html") and os.path.exists(paths["html"]):
                with open(paths["html"]) as f:
                    html_body = f.read()
                msg.add_alternative(html_body, subtype="html")

            # JSON attachment
            if paths.get("json") and os.path.exists(paths["json"]):
                with open(paths["json"], "rb") as f:
                    msg.add_attachment(
                        f.read(),
                        maintype="application",
                        subtype="json",
                        filename=f"session_{session_id}.json",
                    )

            with smtplib.SMTP(self.host, self.port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.user, self.pwd)
                server.send_message(msg)

            logger.info(f"Email sent to {self.to}")
            return True
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return False
