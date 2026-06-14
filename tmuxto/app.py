import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from tmux_conn import TmuxConn

app = FastAPI(title="tmuxto")
conn = TmuxConn()

BASE = Path(__file__).parent
CONNS_FILE = BASE / "connections.json"


# ── Saved connections ─────────────────────────────────────────────────────────

def _load_conns() -> list:
    try:
        return json.loads(CONNS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_conns(entries: list) -> None:
    CONNS_FILE.write_text(json.dumps(entries, indent=2))


# ── API models ────────────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    type: str  # "local" or "ssh"
    name: Optional[str] = None
    host: Optional[str] = None
    port: int = 22
    username: Optional[str] = None
    password: Optional[str] = None
    key_file: Optional[str] = None
    save: bool = False


class SendKeysRequest(BaseModel):
    target: str
    keys: str
    literal: bool = False


class NewWindowRequest(BaseModel):
    session: str
    name: Optional[str] = None


class KillRequest(BaseModel):
    target: str


class ResizePaneRequest(BaseModel):
    target: str
    width: int
    height: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/connect")
def api_connect(req: ConnectRequest):
    if req.type == "local":
        result = conn.connect_local()
    elif req.type == "ssh":
        if not req.host or not req.username:
            return JSONResponse({"success": False, "error": "host and username required"}, 400)
        result = conn.connect_ssh(
            host=req.host,
            username=req.username,
            password=req.password or None,
            key_file=req.key_file or None,
            port=req.port,
        )
    else:
        return JSONResponse({"success": False, "error": "type must be 'local' or 'ssh'"}, 400)

    if result["success"] and req.save and req.type == "ssh":
        entries = _load_conns()
        entry = {
            "name": req.name or req.host,
            "type": "ssh",
            "host": req.host,
            "port": req.port,
            "username": req.username,
            "key_file": req.key_file or "",
            "password": req.password or "",
        }
        entries = [e for e in entries if e.get("name") != entry["name"]]
        entries.insert(0, entry)
        _save_conns(entries[:20])

    return result


@app.post("/api/disconnect")
def api_disconnect():
    conn.disconnect()
    return {"success": True}


@app.get("/api/status")
def api_status():
    return {
        "connected": conn.connected,
        "mode": conn._mode,
        "host": conn.host,
    }


@app.get("/api/connections")
def api_connections():
    return {"connections": _load_conns()}


@app.delete("/api/connections/{name}")
def api_delete_connection(name: str):
    entries = [e for e in _load_conns() if e.get("name") != name]
    _save_conns(entries)
    return {"success": True}


@app.post("/api/send-keys")
def api_send_keys(req: SendKeysRequest):
    if not conn.connected:
        return JSONResponse({"success": False, "error": "not connected"}, 400)
    conn.send_keys(req.target, req.keys, literal=req.literal)
    return {"success": True}


@app.post("/api/new-window")
def api_new_window(req: NewWindowRequest):
    if not conn.connected:
        return JSONResponse({"success": False, "error": "not connected"}, 400)
    conn.new_window(req.session, req.name)
    return {"success": True}


@app.post("/api/kill-pane")
def api_kill_pane(req: KillRequest):
    if not conn.connected:
        return JSONResponse({"success": False, "error": "not connected"}, 400)
    conn.kill_pane(req.target)
    return {"success": True}


@app.post("/api/resize-pane")
def api_resize_pane(req: ResizePaneRequest):
    if not conn.connected:
        return JSONResponse({"success": False, "error": "not connected"}, 400)
    conn.resize_pane(req.target, req.width, req.height)
    return {"success": True}


@app.post("/api/kill-window")
def api_kill_window(req: KillRequest):
    if not conn.connected:
        return JSONResponse({"success": False, "error": "not connected"}, 400)
    conn.kill_window(req.target)
    return {"success": True}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_handler(ws: WebSocket, interval: float = 1.0):
    interval = max(0.2, min(10.0, interval))
    await ws.accept()
    try:
        while True:
            if conn.connected:
                try:
                    tree = await asyncio.get_event_loop().run_in_executor(
                        None, conn.get_tree
                    )
                    await ws.send_text(json.dumps({"sessions": tree}))
                except Exception as exc:
                    await ws.send_text(json.dumps({"error": str(exc)}))
            else:
                # Auto-reconnect SSH connections
                if conn._mode == "ssh" and conn._conn_params:
                    try:
                        await asyncio.get_event_loop().run_in_executor(None, conn._reconnect)
                    except Exception:
                        pass
                await ws.send_text(json.dumps({"sessions": None}))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ── Static files ──────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8007, log_level="info")
