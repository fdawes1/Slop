import csv
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, Response, send_file

app = Flask(__name__)

HIDRIVE_ROOT  = Path("/mnt/hidrive/public")
LOGS_DIR      = Path(__file__).parent / "logs"
SESSIONS_FILE = Path(__file__).parent / "sessions.json"
LOGS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------

def _load_sessions() -> dict:
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text())
        except Exception:
            pass
    return {}

def _save_sessions():
    SESSIONS_FILE.write_text(json.dumps(_sessions, indent=2))

_sessions = _load_sessions()  # session_id -> {operator, log_path}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_path(rel):
    """Resolve and verify path stays within HIDRIVE_ROOT."""
    resolved = (HIDRIVE_ROOT / rel).resolve()
    if not str(resolved).startswith(str(HIDRIVE_ROOT.resolve())):
        return None
    return resolved

def _ppx_from_unit(unit):
    m = re.search(r"\d+", unit)
    return str(int(m.group())) if m else unit

def _operator_log_path(operator: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", operator.strip())
    return LOGS_DIR / f"{safe}.csv"


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Browse API
# ---------------------------------------------------------------------------

@app.route("/api/units")
def api_units():
    if not HIDRIVE_ROOT.is_dir():
        return jsonify([])
    units = [
        d for d in sorted(os.listdir(HIDRIVE_ROOT))
        if re.match(r"PikPak", d) and (HIDRIVE_ROOT / d).is_dir()
    ]
    return jsonify(units)


@app.route("/api/units/<unit>/dates")
def api_dates(unit):
    unit_path = HIDRIVE_ROOT / unit
    if not unit_path.is_dir():
        return jsonify([])
    dates = []
    for year in sorted(os.listdir(unit_path)):
        if not year.isdigit():
            continue
        year_path = unit_path / year
        if not year_path.is_dir():
            continue
        for month in sorted(os.listdir(year_path)):
            month_path = year_path / month
            if not month_path.is_dir():
                continue
            for day in sorted(os.listdir(month_path)):
                if (month_path / day).is_dir():
                    dates.append(f"{year}-{month}-{day}")
    return jsonify(dates)


@app.route("/api/units/<unit>/dates/<date>/videos")
def api_videos(unit, date):
    parts = date.split("-")
    if len(parts) != 3:
        return jsonify([])
    year, month, day = parts
    folder = _safe_path(f"{unit}/{year}/{month}/{day}")
    if not folder or not folder.is_dir():
        return jsonify([])
    videos = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(".mp4"):
            m = re.search(r"(\d{14})", f)
            if m:
                ts = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
                videos.append({
                    "filename": f,
                    "label": ts.strftime("%H:%M:%S"),
                    "path": f"{unit}/{year}/{month}/{day}/{f}",
                    "start_iso": ts.isoformat(),
                })
    return jsonify(videos)


# ---------------------------------------------------------------------------
# Video streaming — range requests required for browser seeking/preloading
# ---------------------------------------------------------------------------

@app.route("/video/<path:video_path>")
def serve_video(video_path):
    full_path = _safe_path(video_path)
    if not full_path or not full_path.exists():
        return "Not found", 404

    file_size    = full_path.stat().st_size
    range_header = request.headers.get("Range")

    if not range_header:
        resp = send_file(full_path, mimetype="video/mp4", conditional=True)
        resp.headers["Accept-Ranges"] = "bytes"
        return resp

    m = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not m:
        return "Bad range", 400

    start  = int(m.group(1))
    end    = int(m.group(2)) if m.group(2) else file_size - 1
    end    = min(end, file_size - 1)
    length = end - start + 1

    def generate():
        with open(full_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return Response(
        generate(),
        status=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": "video/mp4",
        },
    )


# ---------------------------------------------------------------------------
# Session & logging
# ---------------------------------------------------------------------------

@app.route("/api/session", methods=["POST"])
def create_session():
    operator   = (request.json or {}).get("operator", "unknown").strip()
    session_id = uuid.uuid4().hex[:10]
    log_path   = _operator_log_path(operator)

    # Write header only when creating a fresh file
    if not log_path.exists() or log_path.stat().st_size == 0:
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow(["PPX", "Date", "Time", "Index", "Status", "Product", "Operator"])

    _sessions[session_id] = {"operator": operator, "log_path": str(log_path)}
    _save_sessions()
    return jsonify({"session_id": session_id})


@app.route("/api/session/<session_id>/verify")
def verify_session(session_id):
    sess = _sessions.get(session_id)
    if not sess:
        return jsonify({"valid": False}), 404
    return jsonify({"valid": True, "operator": sess["operator"]})


@app.route("/api/log", methods=["POST"])
def log_event():
    data = request.json or {}
    sess = _sessions.get(data.get("session_id"))
    if not sess:
        return jsonify({"error": "invalid session"}), 400

    ppx = _ppx_from_unit(data.get("unit", ""))
    try:
        ts       = datetime.fromisoformat(data["timestamp"])
        date_str = f"{ts.month}/{ts.day}/{ts.year}"
        time_str = f"{ts.hour}:{ts.minute:02d}:{ts.second:02d}"
    except Exception:
        date_str = time_str = ""

    with open(sess["log_path"], "a", newline="") as f:
        csv.writer(f).writerow([
            ppx, date_str, time_str, "",
            data.get("status", ""),
            data.get("product", ""),
            sess["operator"],
        ])

    return jsonify({"ok": True})


@app.route("/api/log/undo", methods=["POST"])
def undo_event():
    data = request.json or {}
    sess = _sessions.get(data.get("session_id"))
    if not sess:
        return jsonify({"error": "invalid session"}), 400

    p = Path(sess["log_path"])
    if not p.exists():
        return jsonify({"removed": False})

    lines = p.read_bytes().splitlines(keepends=True)
    # Keep the header; remove the last data row if one exists
    if len(lines) <= 1:
        return jsonify({"removed": False})

    p.write_bytes(b"".join(lines[:-1]))
    return jsonify({"removed": True})


@app.route("/api/session/<session_id>/download")
def download_log(session_id):
    sess = _sessions.get(session_id)
    if not sess:
        return "Session not found", 404
    p = Path(sess["log_path"])
    if not p.exists():
        return "Log not found", 404
    return send_file(p, as_attachment=True, download_name=p.name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
