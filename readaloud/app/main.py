"""readaloud API — upload a book, get it read back to you.

Pure JSON/file REST API, deliberately kept separate from the bundled web
frontend under /static so any future client (Android app included) can
talk to the same endpoints.
"""

import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import cast, metadata
from app.extract import chunk_text, extract_embedded_metadata, extract_text
from app.tts import DEFAULT_RATE, DEFAULT_VOICE, VOICES, cache_key, synthesize

STORAGE = Path(__file__).resolve().parent.parent / "storage"
BOOKS_DIR = STORAGE / "books"
AUDIO_DIR = STORAGE / "audio"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

TEXT_SUFFIXES = {".txt", ".pdf", ".epub"}
AUDIO_SUFFIXES = {".mp3", ".m4a", ".m4b"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | AUDIO_SUFFIXES

AUDIO_MEDIA_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
}

app = FastAPI(title="readaloud")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def meta_path(book_id: str) -> Path:
    return BOOKS_DIR / book_id / "meta.json"


def load_meta(book_id: str) -> dict:
    path = meta_path(book_id)
    if not path.exists():
        raise HTTPException(404, "book not found")
    return json.loads(path.read_text())


def save_meta(book_id: str, meta: dict) -> None:
    meta_path(book_id).write_text(json.dumps(meta, indent=2))


@app.get("/api/voices")
def list_voices():
    return {"voices": VOICES, "default": DEFAULT_VOICE}


@app.get("/api/books")
def list_books():
    books = []
    if BOOKS_DIR.exists():
        for d in sorted(BOOKS_DIR.iterdir()):
            mp = d / "meta.json"
            if mp.exists():
                books.append(json.loads(mp.read_text()))
    return {"books": books}


@app.post("/api/books")
async def upload_book(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(400, f"unsupported file type {suffix!r}, use .txt/.pdf/.epub/.mp3/.m4a/.m4b")

    book_id = uuid.uuid4().hex[:12]
    book_dir = BOOKS_DIR / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    original_path = book_dir / f"original{suffix}"
    data = await file.read()
    original_path.write_bytes(data)

    filename_title = Path(file.filename or book_id).stem
    is_audio = suffix in AUDIO_SUFFIXES

    embedded = {"title": None, "author": None}
    if is_audio:
        num_chunks = 1
    else:
        try:
            text = extract_text(original_path, suffix)
        except Exception as exc:
            raise HTTPException(400, f"could not extract text: {exc}") from exc

        chunks = chunk_text(text)
        (book_dir / "chunks.json").write_text(json.dumps(chunks))
        num_chunks = len(chunks)
        embedded = extract_embedded_metadata(original_path, suffix)

    title = embedded["title"] or filename_title

    meta = {
        "id": book_id,
        "title": title,
        "author": embedded["author"],
        "cover_url": None,
        "genre": None,
        "year": None,
        "format": suffix.lstrip("."),
        "is_audio": is_audio,
        "num_chunks": num_chunks,
        "current_chunk": 0,
        "voice": DEFAULT_VOICE,
        "rate": DEFAULT_RATE,
        "added_at": time.time(),
    }

    found = await run_in_threadpool(metadata.lookup, title, embedded["author"])
    if found:
        meta["author"] = meta["author"] or found["author"]
        meta["cover_url"] = found["cover_url"]
        meta["genre"] = found["genre"]
        meta["year"] = found["year"]

    save_meta(book_id, meta)
    return meta


@app.get("/api/books/{book_id}")
def get_book(book_id: str):
    return load_meta(book_id)


@app.get("/api/books/{book_id}/chunks/{index}")
def get_chunk_text(book_id: str, index: int):
    meta = load_meta(book_id)
    if not (0 <= index < meta["num_chunks"]):
        raise HTTPException(404, "chunk out of range")
    if meta.get("is_audio"):
        return {"index": index, "text": None, "num_chunks": meta["num_chunks"]}
    chunks = json.loads((BOOKS_DIR / book_id / "chunks.json").read_text())
    return {"index": index, "text": chunks[index], "num_chunks": meta["num_chunks"]}


@app.patch("/api/books/{book_id}/progress")
def update_progress(book_id: str, current_chunk: int):
    meta = load_meta(book_id)
    if not (0 <= current_chunk < meta["num_chunks"]):
        raise HTTPException(400, "current_chunk out of range")
    meta["current_chunk"] = current_chunk
    save_meta(book_id, meta)
    return meta


@app.patch("/api/books/{book_id}/settings")
def update_settings(book_id: str, voice: str | None = None, rate: str | None = None):
    meta = load_meta(book_id)
    if voice:
        if voice not in VOICES:
            raise HTTPException(400, f"unknown voice {voice!r}")
        meta["voice"] = voice
    if rate:
        meta["rate"] = rate
    save_meta(book_id, meta)
    return meta


@app.delete("/api/books/{book_id}")
def delete_book(book_id: str):
    import shutil

    book_dir = BOOKS_DIR / book_id
    if not book_dir.exists():
        raise HTTPException(404, "book not found")
    shutil.rmtree(book_dir)
    shutil.rmtree(AUDIO_DIR / book_id, ignore_errors=True)
    return {"deleted": book_id}


@app.get("/api/books/{book_id}/audio/{index}")
async def get_chunk_audio(book_id: str, index: int, voice: str | None = None, rate: str | None = None):
    meta = load_meta(book_id)
    if not (0 <= index < meta["num_chunks"]):
        raise HTTPException(404, "chunk out of range")

    if meta.get("is_audio"):
        suffix = f".{meta['format']}"
        original_path = BOOKS_DIR / book_id / f"original{suffix}"
        return FileResponse(original_path, media_type=AUDIO_MEDIA_TYPES.get(suffix, "audio/mpeg"))

    voice = voice or meta["voice"]
    rate = rate or meta["rate"]
    chunks = json.loads((BOOKS_DIR / book_id / "chunks.json").read_text())
    text = chunks[index]

    key = cache_key(text, voice, rate)
    out_path = AUDIO_DIR / book_id / f"{key}.mp3"
    if not out_path.exists():
        if not text.strip():
            raise HTTPException(422, "chunk has no readable text")
        await synthesize(text, out_path, voice=voice, rate=rate)

    return FileResponse(out_path, media_type="audio/mpeg")


@app.get("/api/cast/devices")
def list_cast_devices():
    return {"devices": cast.discover_devices()}


@app.post("/api/books/{book_id}/cast")
def start_casting(book_id: str, request: Request, device_name: str, index: int | None = None):
    meta = load_meta(book_id)
    start_index = meta["current_chunk"] if index is None else index
    if not (0 <= start_index < meta["num_chunks"]):
        raise HTTPException(400, "index out of range")

    try:
        result = cast.start_cast(
            book_id,
            device_name,
            start_index,
            str(request.base_url),
            meta,
            load_meta,
            save_meta,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc

    meta["current_chunk"] = start_index
    save_meta(book_id, meta)
    return result


@app.post("/api/books/{book_id}/cast/stop")
def stop_casting(book_id: str):
    if not cast.stop_cast(book_id):
        raise HTTPException(404, "no active cast session for this book")
    return {"casting": False}


@app.get("/api/books/{book_id}/cast/status")
def get_cast_status(book_id: str):
    return cast.cast_status(book_id) or {"casting": False}


BOOKS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
