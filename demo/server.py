#!/usr/bin/env python3
"""
Slop TUI Demo Server
Spawns each TUI app in a PTY and bridges it over WebSocket to xterm.js
"""

import asyncio
import json
import os
import select
import signal
import sys
from pathlib import Path

import ptyprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

SLOP_DIR = Path(__file__).parent.parent.resolve()

APPS = [
    {"id": "trebuchet", "label": "TREBUCHET", "desc": "Physics simulator", "cmd": ["python3", "trebuchet.py"]},
    {"id": "plague",    "label": "PLAGUE",    "desc": "SIR epidemic model", "cmd": ["python3", "plague.py"]},
    {"id": "gravity",   "label": "GRAVITY",   "desc": "N-body orbital sim", "cmd": ["python3", "gravity.py"]},
    {"id": "sandpit",   "label": "SANDPIT",   "desc": "Falling sand sim", "cmd": ["python3", "sandpit.py"]},
    {"id": "sortrace",  "label": "SORTRACE",  "desc": "Algorithm race", "cmd": ["python3", "sortrace.py"]},
    {"id": "swarm",     "label": "SWARM",     "desc": "Boids flocking", "cmd": ["python3", "swarm.py"]},
    {"id": "pendulum",  "label": "PENDULUM",  "desc": "Double pendulum chaos", "cmd": ["python3", "pendulum.py"]},
    {"id": "diffusion", "label": "DIFFUSION", "desc": "Gray-Scott reaction", "cmd": ["python3", "diffusion.py"]},
    {"id": "life",      "label": "LIFE",      "desc": "Conway's Game of Life", "cmd": ["python3", "life.py"]},
    {"id": "maze",      "label": "MAZE",      "desc": "4 solvers racing", "cmd": ["python3", "maze.py"]},
    {"id": "fourier",   "label": "FOURIER",   "desc": "Epicycles animator", "cmd": ["python3", "fourier.py"]},
    {"id": "terrain",   "label": "TERRAIN",   "desc": "Procedural terrain", "cmd": ["python3", "terrain.py"]},
]

HTML = open(Path(__file__).parent / "index.html").read()

app = FastAPI()


@app.get("/")
async def root():
    return HTMLResponse(HTML)


@app.get("/apps")
async def list_apps():
    return APPS


@app.websocket("/ws/{app_id}")
async def ws_terminal(websocket: WebSocket, app_id: str):
    conf = next((a for a in APPS if a["id"] == app_id), None)
    if not conf:
        await websocket.close(code=4004)
        return

    await websocket.accept()

    cwd = str(SLOP_DIR / app_id)
    env = {**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor"}

    try:
        proc = ptyprocess.PtyProcess.spawn(
            conf["cmd"],
            cwd=cwd,
            dimensions=(24, 80),
            env=env,
        )
    except Exception as e:
        await websocket.send_text(json.dumps({"type": "error", "msg": str(e)}))
        await websocket.close()
        return

    loop = asyncio.get_event_loop()
    stop = asyncio.Event()

    async def pty_to_ws():
        while not stop.is_set():
            try:
                ready, _, _ = await loop.run_in_executor(
                    None, select.select, [proc.fd], [], [], 0.05
                )
                if ready:
                    data = await loop.run_in_executor(None, proc.read, 4096)
                    await websocket.send_bytes(data)
                elif not proc.isalive():
                    await websocket.send_text(json.dumps({"type": "exit"}))
                    break
            except (EOFError, OSError):
                try:
                    await websocket.send_text(json.dumps({"type": "exit"}))
                except Exception:
                    pass
                break
            except Exception:
                break

    async def ws_to_pty():
        while not stop.is_set():
            try:
                msg = await websocket.receive()
                if "bytes" in msg:
                    proc.write(msg["bytes"])
                elif "text" in msg:
                    data = json.loads(msg["text"])
                    if data.get("type") == "resize":
                        proc.setwinsize(int(data["rows"]), int(data["cols"]))
            except WebSocketDisconnect:
                break
            except Exception:
                break

    t1 = asyncio.create_task(pty_to_ws())
    t2 = asyncio.create_task(ws_to_pty())
    await asyncio.wait([t1, t2], return_when=asyncio.FIRST_COMPLETED)

    stop.set()
    t1.cancel()
    t2.cancel()

    if proc.isalive():
        try:
            proc.terminate(force=True)
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    print(f"Slop TUI Demo → http://localhost:8099")
    uvicorn.run(app, host="0.0.0.0", port=8099, log_level="warning")
