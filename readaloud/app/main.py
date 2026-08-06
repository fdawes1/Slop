"""readaloud API — upload a book, get it read back to you.

Pure JSON/file REST API, deliberately kept separate from the bundled web
frontend under /static so any future client (Android app included) can
talk to the same endpoints.
"""

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.extract import chunk_text, extract_text
from app.tts import DEFAULT_RATE, DEFAULT_VOICE, VOICES, cache_key, synthesize

STORAGE = Path(__file__).resolve().parent.parent / "storage"
BOOKS_DIR = STORAGE / "books"
AUDIO_DIR = STORAGE / "audio"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

SUPPORTED_SUFFIXES = {".txt", ".pdf", ".epub"}

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
        raise HTTPException(400, f"unsupported file type {suffix!r}, use .txt/.pdf/.epub")

    book_id = uuid.uuid4().hex[:12]
    book_dir = BOOKS_DIR / book_id
    book_dir.mkdir(parents=True, exist_ok=True)

    original_path = book_dir / f"original{suffix}"
    data = await file.read()
    original_path.write_bytes(data)

    try:
        text = extract_text(original_path, suffix)
    except Exception as exc:
        raise HTTPException(400, f"could not extract text: {exc}") from exc

    chunks = chunk_text(text)
    (book_dir / "chunks.json").write_text(json.dumps(chunks))

    title = Path(file.filename or book_id).stem
    meta = {
        "id": book_id,
        "title": title,
        "format": suffix.lstrip("."),
        "num_chunks": len(chunks),
        "current_chunk": 0,
        "voice": DEFAULT_VOICE,
        "rate": DEFAULT_RATE,
    }
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


BOOKS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
