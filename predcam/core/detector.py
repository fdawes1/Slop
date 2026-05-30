import cv2
import numpy as np
from typing import List, Dict


class MotionDetector:
    def __init__(self):
        self._bg = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=40, detectShadows=False
        )
        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._min_area = 800

    def detect(self, frame: np.ndarray) -> List[Dict]:
        fg = self._bg.apply(frame)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, self._kernel)
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._kernel)
        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        fh, fw = frame.shape[:2]
        detections = []
        for cnt in contours:
            if cv2.contourArea(cnt) < self._min_area:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            detections.append({
                "x": x / fw, "y": y / fh,
                "w": w / fw, "h": h / fh,
            })
        return detections
