"""Google Cast (Chromecast / Google Home) playback.

Discovers devices on the LAN and tells one to pull a chunk's audio
straight from this server's own /api/books/{id}/audio/{index} endpoint —
the speaker streams it directly, no relay through the browser. For
multi-chunk text books, a status listener watches for each chunk
finishing and casts the next one automatically.
"""

import threading
from urllib.parse import quote

import pychromecast
from pychromecast.controllers.media import MediaStatusListener

_lock = threading.Lock()
_sessions: dict[str, dict] = {}  # book_id -> {cast, device_name, index, base_url}

DISCOVERY_TIMEOUT = 10


def discover_devices() -> list[dict]:
    chromecasts, browser = pychromecast.get_chromecasts(timeout=DISCOVERY_TIMEOUT)
    pychromecast.discovery.stop_discovery(browser)
    return [
        {"name": cc.name, "model": cc.model_name, "uuid": str(cc.uuid)}
        for cc in sorted(chromecasts, key=lambda c: c.name)
    ]


def _find_device(device_name: str):
    chromecasts, browser = pychromecast.get_chromecasts(timeout=DISCOVERY_TIMEOUT)
    pychromecast.discovery.stop_discovery(browser)
    for cc in chromecasts:
        if cc.name == device_name:
            return cc
    return None


def _chunk_url(base_url: str, meta: dict, index: int) -> str:
    book_id = meta["id"]
    if meta.get("is_audio"):
        return f"{base_url}api/books/{book_id}/audio/{index}"
    voice = quote(meta["voice"])
    rate = quote(meta["rate"])
    return f"{base_url}api/books/{book_id}/audio/{index}?voice={voice}&rate={rate}"


class _AutoAdvanceListener(MediaStatusListener):
    def __init__(self, book_id: str, load_meta, save_meta):
        self.book_id = book_id
        self._load_meta = load_meta
        self._save_meta = save_meta

    def new_media_status(self, status):
        if status.player_state == "IDLE" and status.idle_reason == "FINISHED":
            _advance(self.book_id, self._load_meta, self._save_meta)

    def load_media_failed(self, queue_item_id, error_code):
        with _lock:
            _sessions.pop(self.book_id, None)


def _advance(book_id: str, load_meta, save_meta) -> None:
    with _lock:
        session = _sessions.get(book_id)
        if not session:
            return
        try:
            meta = load_meta(book_id)
        except Exception:
            # Book was likely deleted mid-cast; drop the session rather than
            # crash whatever pychromecast thread this callback runs on.
            _sessions.pop(book_id, None)
            return
        next_index = session["index"] + 1
        if next_index >= meta["num_chunks"]:
            _sessions.pop(book_id, None)
            return
        session["index"] = next_index
        cast = session["cast"]
        base_url = session["base_url"]

    meta["current_chunk"] = next_index
    save_meta(book_id, meta)
    url = _chunk_url(base_url, meta, next_index)
    cast.media_controller.play_media(url, "audio/mpeg", stream_type="BUFFERED")


def start_cast(book_id: str, device_name: str, index: int, base_url: str, meta: dict, load_meta, save_meta) -> dict:
    device = _find_device(device_name)
    if device is None:
        raise ValueError(f"cast device {device_name!r} not found on the network")

    device.wait(timeout=10)

    with _lock:
        _stop_cast_locked(book_id)
        listener = _AutoAdvanceListener(book_id, load_meta, save_meta)
        device.media_controller.register_status_listener(listener)
        _sessions[book_id] = {
            "cast": device,
            "device_name": device.name,
            "index": index,
            "base_url": base_url,
        }

    url = _chunk_url(base_url, meta, index)
    content_type = "audio/mpeg"
    device.media_controller.play_media(url, content_type, title=meta["title"], stream_type="BUFFERED")
    device.media_controller.block_until_active(timeout=10)

    return {"casting": True, "device": device.name, "index": index}


def _stop_cast_locked(book_id: str) -> bool:
    session = _sessions.pop(book_id, None)
    if not session:
        return False
    cast = session["cast"]
    try:
        cast.media_controller.stop()
    except Exception:
        pass
    try:
        cast.quit_app()
    except Exception:
        pass
    try:
        cast.disconnect(blocking=False)
    except Exception:
        pass
    return True


def stop_cast(book_id: str) -> bool:
    with _lock:
        return _stop_cast_locked(book_id)


def cast_status(book_id: str) -> dict | None:
    session = _sessions.get(book_id)
    if not session:
        return None
    return {"casting": True, "device": session["device_name"], "index": session["index"]}
