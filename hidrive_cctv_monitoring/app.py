import csv
import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, quote

import requests as req_lib
from flask import Flask, request, jsonify, render_template, Response, send_file

app = Flask(__name__)

HIDRIVE_WEBDAV = "https://webdav.hidrive.strato.com"
HIDRIVE_ROOT   = "/public"
LOCAL_ROOT    = Path("/mnt/hidrive/public")
LOGS_DIR      = Path(__file__).parent / "logs"
SESSIONS_FILE = Path(__file__).parent / "sessions.json"
LOGS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class LocalProvider:
    def list_units(self):
        if not LOCAL_ROOT.is_dir():
            return []
        return sorted(
            d for d in os.listdir(LOCAL_ROOT)
            if re.match(r"PikPak", d) and (LOCAL_ROOT / d).is_dir()
        )

    def list_dates(self, unit):
        unit_path = LOCAL_ROOT / unit
        if not unit_path.is_dir():
            return []
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
        return dates

    def list_videos(self, unit, date):
        parts = date.split("-")
        if len(parts) != 3:
            return []
        year, month, day = parts
        folder = self._safe(f"{unit}/{year}/{month}/{day}")
        if not folder or not folder.is_dir():
            return []
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
        return videos

    def serve_video(self, video_path):
        full_path = self._safe(video_path)
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
                "Content-Range":  f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges":  "bytes",
                "Content-Length": str(length),
                "Content-Type":   "video/mp4",
            },
        )

    def _safe(self, rel):
        resolved = (LOCAL_ROOT / rel).resolve()
        if not str(resolved).startswith(str(LOCAL_ROOT.resolve())):
            return None
        return resolved


class HiDriveProvider:
    def __init__(self, username, password, root=HIDRIVE_ROOT):
        self.auth = (username, password)
        self.root = root.rstrip("/")

    def _propfind(self, path):
        """Return list of (name, is_dir) for the children of path."""
        url = f"{HIDRIVE_WEBDAV}{quote(path, safe='/')}"
        r = req_lib.request(
            "PROPFIND", url, auth=self.auth,
            headers={"Depth": "1", "Content-Type": "application/xml"},
            timeout=15,
        )
        r.raise_for_status()
        ns   = {"D": "DAV:"}
        tree = ET.fromstring(r.content)
        out  = []
        for resp in tree.findall("D:response", ns)[1:]:  # skip the dir itself
            href   = unquote(resp.find("D:href", ns).text)
            name   = href.rstrip("/").split("/")[-1]
            is_dir = resp.find(".//D:collection", ns) is not None
            out.append((name, is_dir))
        return out

    def list_units(self):
        entries = self._propfind(f"{self.root}/")
        return sorted(name for name, is_dir in entries
                      if is_dir and re.match(r"PikPak", name))

    def list_dates(self, unit):
        dates     = []
        unit_path = f"{self.root}/{unit}"
        try:
            years = self._propfind(f"{unit_path}/")
        except Exception:
            return []
        for yr, is_dir in years:
            if not is_dir or not yr.isdigit():
                continue
            try:
                months = self._propfind(f"{unit_path}/{yr}/")
            except Exception:
                continue
            for mo, is_dir2 in months:
                if not is_dir2:
                    continue
                try:
                    days = self._propfind(f"{unit_path}/{yr}/{mo}/")
                except Exception:
                    continue
                for day, is_dir3 in days:
                    if is_dir3:
                        dates.append(f"{yr}-{mo}-{day}")
        return sorted(dates)

    def list_videos(self, unit, date):
        parts = date.split("-")
        if len(parts) != 3:
            return []
        year, month, day = parts
        path = f"{self.root}/{unit}/{year}/{month}/{day}"
        try:
            entries = self._propfind(f"{path}/")
        except Exception:
            return []
        videos = []
        for name, is_dir in sorted(entries):
            if is_dir or not name.lower().endswith(".mp4"):
                continue
            ts_m = re.search(r"(\d{14})", name)
            if ts_m:
                ts = datetime.strptime(ts_m.group(1), "%Y%m%d%H%M%S")
                videos.append({
                    "filename":  name,
                    "label":     ts.strftime("%H:%M:%S"),
                    "path":      f"{unit}/{year}/{month}/{day}/{name}",
                    "start_iso": ts.isoformat(),
                })
        return videos

    def serve_video(self, video_path):
        url = f"{HIDRIVE_WEBDAV}{quote(f'{self.root}/{video_path}', safe='/')}"
        hd_headers = {}
        range_header = request.headers.get("Range")
        if range_header:
            hd_headers["Range"] = range_header
        try:
            r = req_lib.get(url, auth=self.auth, headers=hd_headers,
                            stream=True, timeout=30)
            r.raise_for_status()
        except Exception:
            return "Failed to fetch from HiDrive", 502

        def generate():
            for chunk in r.iter_content(65536):
                yield chunk

        resp_headers = {
            "Content-Type":  r.headers.get("Content-Type", "video/mp4"),
            "Accept-Ranges": "bytes",
        }
        for h in ("Content-Range", "Content-Length"):
            if h in r.headers:
                resp_headers[h] = r.headers[h]

        return Response(generate(), status=r.status_code, headers=resp_headers)


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
    # Never persist HiDrive sessions — credentials must not land on disk
    to_save = {sid: s for sid, s in _sessions.items() if s.get("source", "local") == "local"}
    SESSIONS_FILE.write_text(json.dumps(to_save, indent=2))

_sessions  = _load_sessions()
_providers = {}

# Reconstruct providers for persisted local sessions
for _sid in list(_sessions.keys()):
    _providers[_sid] = LocalProvider()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ppx_from_unit(unit):
    m = re.search(r"\d+", unit)
    return str(int(m.group())) if m else unit

def _operator_log_path(operator: str) -> Path:
    safe = re.sub(r"[^\w\-]", "_", operator.strip())
    return LOGS_DIR / f"{safe}.csv"

def _get_provider():
    sid = request.cookies.get("cctv_sid")
    if sid and sid in _providers:
        return _providers[sid]
    return LocalProvider()


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
    try:
        return jsonify(_get_provider().list_units())
    except Exception:
        return jsonify([])


@app.route("/api/units/<unit>/dates")
def api_dates(unit):
    try:
        return jsonify(_get_provider().list_dates(unit))
    except Exception:
        return jsonify([])


@app.route("/api/units/<unit>/dates/<date>/videos")
def api_videos(unit, date):
    try:
        return jsonify(_get_provider().list_videos(unit, date))
    except Exception:
        return jsonify([])


# ---------------------------------------------------------------------------
# Video streaming
# ---------------------------------------------------------------------------

@app.route("/video/<path:video_path>")
def serve_video(video_path):
    return _get_provider().serve_video(video_path)


# ---------------------------------------------------------------------------
# Session & logging
# ---------------------------------------------------------------------------

@app.route("/api/session", methods=["POST"])
def create_session():
    data       = request.json or {}
    operator   = data.get("operator", "unknown").strip()
    source     = data.get("source", "local")
    session_id = uuid.uuid4().hex[:10]
    log_path   = _operator_log_path(operator)

    if source == "hidrive":
        hd_user = data.get("hidrive_user", "").strip()
        hd_pass = data.get("hidrive_pass", "")
        hd_root = (data.get("hidrive_root") or HIDRIVE_ROOT).strip()
        provider = HiDriveProvider(hd_user, hd_pass, hd_root)
        try:
            provider.list_units()  # validate credentials
        except req_lib.exceptions.HTTPError as e:
            code = e.response.status_code
            if code in (401, 403):
                return jsonify({"error": "Invalid HiDrive credentials"}), 401
            return jsonify({"error": f"HiDrive error {code}"}), 502
        except Exception as e:
            return jsonify({"error": f"HiDrive connection failed: {e}"}), 502
        _providers[session_id] = provider
    else:
        _providers[session_id] = LocalProvider()

    if not log_path.exists() or log_path.stat().st_size == 0:
        with open(log_path, "w", newline="") as f:
            csv.writer(f).writerow(["PPX", "Date", "Time", "Index", "Status", "Product", "Operator"])

    _sessions[session_id] = {"operator": operator, "log_path": str(log_path), "source": source}
    _save_sessions()
    return jsonify({"session_id": session_id, "source": source})


@app.route("/api/session/<session_id>/verify")
def verify_session(session_id):
    sess = _sessions.get(session_id)
    if not sess:
        return jsonify({"valid": False}), 404
    # HiDrive sessions aren't persisted, so they die on server restart
    if sess.get("source") == "hidrive" and session_id not in _providers:
        return jsonify({"valid": False}), 404
    return jsonify({"valid": True, "operator": sess["operator"], "source": sess.get("source", "local")})


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
