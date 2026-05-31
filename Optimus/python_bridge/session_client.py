"""
session_client.py
Calls the EC2 FastAPI backend to create and end interview sessions.
Returns the WireGuard config string needed to activate the OS-level tunnel.
"""

import requests
import logging
import os

logger = logging.getLogger("SessionClient")

EC2_BASE_URL = os.getenv("COADEX_BACKEND_URL", "http://3.235.42.166:8000")
TIMEOUT = 10  # seconds


def check_backend_reachable() -> bool:
    """Ping the /health endpoint to verify the backend is up."""
    try:
        r = requests.get(f"{EC2_BASE_URL}/health", timeout=TIMEOUT)
        return r.status_code == 200
    except Exception:
        return False


def start_session(candidate_id: str) -> dict:
    """
    Call POST /session/start on EC2.
    Returns:
        { session_id, wg_config, client_ip, peer_registered, status }
    Raises:
        RuntimeError on network failure or non-200 response.
    """
    try:
        resp = requests.post(
            f"{EC2_BASE_URL}/session/start",
            json={"candidate_id": candidate_id},
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Session started: {data['session_id']} | IP: {data['client_ip']}")
        return data
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Cannot reach EC2 backend at {EC2_BASE_URL}. Check your internet connection.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Backend error: {e.response.status_code} — {e.response.text}")
    except Exception as e:
        raise RuntimeError(f"Session start failed: {e}")


def end_session(session_id: str) -> bool:
    """
    Call POST /session/end/{session_id} on EC2.
    Returns True on success, False on failure.
    """
    try:
        resp = requests.post(f"{EC2_BASE_URL}/session/end/{session_id}", timeout=TIMEOUT)
        resp.raise_for_status()
        logger.info(f"Session {session_id} ended.")
        return True
    except Exception as e:
        logger.error(f"Failed to end session {session_id}: {e}")
        return False


if __name__ == "__main__":
    import sys
    import json
    
    # Configure logging to go ONLY to stderr so stdout remains pure JSON
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    
    try:
        if "--health" in sys.argv:
            print(json.dumps({"reachable": check_backend_reachable()}))
        elif "--start" in sys.argv:
            idx = sys.argv.index("--start")
            candidate_id = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "test-candidate-001"
            result = start_session(candidate_id)
            print(json.dumps(result))
        elif "--end" in sys.argv:
            idx = sys.argv.index("--end")
            if len(sys.argv) > idx + 1:
                success = end_session(sys.argv[idx + 1])
                print(json.dumps({"success": success}))
            else:
                print(json.dumps({"error": "Missing session ID"}))
        else:
            print(json.dumps({"error": "Invalid arguments"}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
