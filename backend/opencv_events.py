"""
Optimus OpenCV Monitor – optional facial integrity detection.
If OpenCV is not installed, this module is silently skipped.
"""
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("OpenCVMonitor")

try:
    import cv2
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False
    logger.info("OpenCV not installed — facial monitoring disabled.")

FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml" if _CV2_AVAILABLE else ""


class OpenCVMonitor:
    """
    Runs face detection in a background thread.
    Calls on_event(event_type, details) when anomalies are detected.
    event_type: 'NO_FACE' | 'MULTIPLE_FACES' | 'FACE_OK'
    """

    def __init__(self, on_event: Callable, check_interval: float = 2.0):
        if not _CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) is not installed.")
        self.on_event       = on_event
        self.check_interval = check_interval
        self._face_cascade  = cv2.CascadeClassifier(FACE_CASCADE_PATH)
        self._cap: Optional[cv2.VideoCapture] = None
        self._running       = False
        self._thread: Optional[threading.Thread] = None
        self._last_status   = "FACE_OK"

    def start(self):
        self._cap     = cv2.VideoCapture(0)
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("OpenCV face monitor started.")

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
        logger.info("OpenCV face monitor stopped.")

    def _loop(self):
        consecutive_no_face = 0
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(self.check_interval)
                continue
            gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self._face_cascade.detectMultiScale(gray, 1.1, 5)
            count = len(faces)
            if count == 0:
                consecutive_no_face += 1
                if consecutive_no_face >= 3:       # 3 consecutive → alert
                    if self._last_status != "NO_FACE":
                        self._last_status = "NO_FACE"
                        self.on_event("NO_FACE", {"consecutive": consecutive_no_face})
            elif count > 1:
                consecutive_no_face = 0
                if self._last_status != "MULTIPLE_FACES":
                    self._last_status = "MULTIPLE_FACES"
                    self.on_event("MULTIPLE_FACES", {"count": count})
            else:
                consecutive_no_face = 0
                if self._last_status != "FACE_OK":
                    self._last_status = "FACE_OK"
                    self.on_event("FACE_OK", {})
            time.sleep(self.check_interval)
