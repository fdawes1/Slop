#!/usr/bin/env python3
"""predcam — Predator-vision multi-source camera server"""

from __future__ import annotations

import asyncio
import base64
import json
import socket
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.detector import MotionDetector
from core.sources import SourceManager

# ── Setup ──────────────────────────────────────────────────────────────────────

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    sources.probe_usb()
    asyncio.create_task(_local_loop())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

sources = SourceManager()
detector = MotionDetector()
viewers: list[WebSocket] = []

# ── HTTP ───────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")

@app.get("/cam")
async def cam():
    return FileResponse(STATIC / "cam.html")

@app.get("/api/sources")
async def list_sources():
    return sources.list_sources()

@app.post("/api/sources/{src_id:path}")
async def select_source(src_id: str):
    ok = sources.select(src_id)
    return {"ok": ok, "selected": src_id}

# ── Broadcast ──────────────────────────────────────────────────────────────────

async def broadcast(jpeg_bytes: bytes, source_id: str) -> None:
    if not viewers:
        return

    nparr = np.frombuffer(jpeg_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    detections = detector.detect(frame) if frame is not None else []

    payload = json.dumps({
        "type": "frame",
        "source": source_id,
        "data": base64.b64encode(jpeg_bytes).decode(),
        "detections": detections,
        "ts": time.time(),
    })

    dead = []
    for v in viewers:
        try:
            await v.send_text(payload)
        except Exception:
            dead.append(v)
    for v in dead:
        viewers.remove(v)

# ── WebSockets ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/view")
async def ws_view(ws: WebSocket):
    await ws.accept()
    viewers.append(ws)
    try:
        while True:
            await asyncio.sleep(30)   # keepalive
    except WebSocketDisconnect:
        pass
    finally:
        if ws in viewers:
            viewers.remove(ws)


@app.websocket("/ws/send")
async def ws_send(ws: WebSocket):
    """Phone or external sender pushes JPEG frames here."""
    await ws.accept()
    sources.register_phone()
    try:
        while True:
            data = await ws.receive_bytes()
            await broadcast(data, "phone")
    except WebSocketDisconnect:
        pass
    finally:
        sources.unregister_phone()

# ── Local camera loop ──────────────────────────────────────────────────────────

async def _local_loop() -> None:
    while True:
        if not sources.is_phone_active():
            cap = sources.active_capture()
            if cap is not None:
                ret, frame = cap.read()
                if ret:
                    _, jpeg = cv2.imencode(
                        ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75]
                    )
                    await broadcast(jpeg.tobytes(), sources.active_id())
        await asyncio.sleep(1 / 15)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "localhost"

    ssl_args = {}
    if Path("cert.pem").exists() and Path("key.pem").exists():
        ssl_args = {"ssl_certfile": "cert.pem", "ssl_keyfile": "key.pem"}
        proto = "https"
        print("HTTPS enabled — iOS camera will work")
    else:
        proto = "http"
        print("HTTP mode — Android Chrome works; for iOS run ./gen_cert.sh first")

    print(f"\n  HUD viewer : {proto}://{local_ip}:8080/")
    print(f"  Phone cam  : {proto}://{local_ip}:8080/cam\n")

    uvicorn.run("server:app", host="0.0.0.0", port=8080, **ssl_args)
