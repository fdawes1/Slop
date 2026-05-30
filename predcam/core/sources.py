from __future__ import annotations

import os
import cv2
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Source:
    id: str
    name: str
    kind: str   # "usb" | "rtsp" | "mjpeg" | "ws"
    uri: str = ""


class SourceManager:
    def __init__(self) -> None:
        self._sources: Dict[str, Source] = {}
        self._active_id: Optional[str] = None
        self._capture: Optional[cv2.VideoCapture] = None

    def probe_usb(self, max_devices: int = 4) -> None:
        # Silence OpenCV's stderr during probing
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        saved_stderr = os.dup(2)
        os.dup2(devnull_fd, 2)
        try:
            for i in range(max_devices):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    src_id = f"usb:{i}"
                    self._sources[src_id] = Source(
                        id=src_id, name=f"USB Camera {i}", kind="usb", uri=str(i)
                    )
                    cap.release()
        finally:
            os.dup2(saved_stderr, 2)
            os.close(saved_stderr)
            os.close(devnull_fd)
        if not self._active_id:
            for src_id, src in self._sources.items():
                if src.kind == "usb":
                    self.select(src_id)
                    break

    def add_rtsp(self, url: str, name: str = "") -> str:
        src_id = f"rtsp:{url}"
        self._sources[src_id] = Source(
            id=src_id, name=name or url, kind="rtsp", uri=url
        )
        return src_id

    def register_phone(self) -> None:
        src_id = "ws:phone"
        self._sources[src_id] = Source(id=src_id, name="Phone Camera", kind="ws")
        # Phone takes priority — pause any local capture
        if self._capture:
            self._capture.release()
            self._capture = None
        self._active_id = src_id

    def unregister_phone(self) -> None:
        self._sources.pop("ws:phone", None)
        if self._active_id == "ws:phone":
            self._active_id = None
            # Fall back to first USB camera
            for src_id, src in self._sources.items():
                if src.kind == "usb":
                    self.select(src_id)
                    break

    def select(self, src_id: str) -> bool:
        src = self._sources.get(src_id)
        if not src:
            return False
        if self._capture:
            self._capture.release()
            self._capture = None
        self._active_id = src_id
        if src.kind in ("usb", "rtsp"):
            uri: int | str = int(src.uri) if src.kind == "usb" else src.uri
            self._capture = cv2.VideoCapture(uri)
        return True

    def active_capture(self) -> Optional[cv2.VideoCapture]:
        return self._capture

    def active_id(self) -> str:
        return self._active_id or "none"

    def is_phone_active(self) -> bool:
        return self._active_id == "ws:phone"

    def list_sources(self) -> List[dict]:
        return [
            {"id": s.id, "name": s.name, "kind": s.kind, "active": s.id == self._active_id}
            for s in self._sources.values()
        ]
