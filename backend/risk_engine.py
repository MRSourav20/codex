import logging
from backend.dns_monitor.dns_logger import DNSLogger
from backend.session_manager import SessionManager

logger = logging.getLogger("RiskEngine")

class RiskEngine:
    """
    Computes a risk score from 0-100 based on session events.
    0–30: Low
    31–70: Medium
    71–100: High
    """
    def __init__(self):
        self.dns_logger = DNSLogger()
        self.session_manager = SessionManager()
        
        # Risk weights (points added to total score)
        self.weights = {
            "AI_DOMAIN_BURST": 40,
            "SUSPICIOUS_DOMAIN": 20,
            "DOMAIN_SWITCHING": 15,
            "OPENCV_MULTIPLE_FACES": 50,
            "OPENCV_FACE_MISSING_PROLONGED": 40,
        }

    def evaluate_session(self, session_id: str) -> dict:
        """
        Evaluate and return aggregate score for a session based on suspicious events.
        """
        events = self.dns_logger.get_suspicious_events(limit=500, session_id=session_id)
        
        total_score = 0
        event_counts = {}
        
        for event in events:
            event_type = event["event_type"]
            count = event["count"]
            
            # Record frequency
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += count
            
            # Apply weight
            weight = self.weights.get(event_type, 10) # default 10 per unknown suspicious event
            
            # Add to score - we allow compounding but max 100
            total_score += (weight * count)
        
        # Cap score at 100
        score = min(max(total_score, 0), 100)
        
        # Determine level
        if score <= 30:
            level = "Low"
        elif score <= 70:
            level = "Medium"
        else:
            level = "High"
            
        # Optional: Save back to the session database so it persists
        self.session_manager.update_risk_score(session_id, score)
            
        return {
            "score": score,
            "level": level,
            "event_counts": event_counts
        }

if __name__ == '__main__':
    # Test
    r = RiskEngine()
    print(r.evaluate_session("test_session"))
