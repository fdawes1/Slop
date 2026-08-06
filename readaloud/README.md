# readaloud

Drop a book in, it reads it back to you. TXT / PDF / EPUB in, narrated audio out, via [edge-tts](https://github.com/rany2/edge-tts) (free, no API key).

Currently a local web app. The backend is a plain JSON/file REST API kept separate from the bundled web frontend, so a future Android client can talk to the same endpoints without a rewrite.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — drag a book in, pick a voice/speed, hit play. Progress and per-book voice/speed are saved, so it picks up where you left off.

## How it works

- `app/extract.py` — pulls plain text out of the upload (pypdf for PDF, ebooklib+BeautifulSoup for EPUB) and splits it into paragraph-aware chunks (~1800 chars each) for TTS.
- `app/tts.py` — renders a chunk to mp3 via edge-tts, cached on disk keyed by (text, voice, rate) so nothing is re-synthesized on replay.
- `app/main.py` — FastAPI REST API: upload, list, fetch chunk text/audio, update progress/voice/rate, delete.
- `static/` — the web frontend (vanilla HTML/JS), consumes the API only.

Uploaded books and generated audio live under `storage/` (git-ignored).

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/voices` | Available TTS voices |
| `GET` | `/api/books` | List books + progress |
| `POST` | `/api/books` | Upload a book (multipart `file`) |
| `GET` | `/api/books/{id}` | Book metadata |
| `GET` | `/api/books/{id}/chunks/{i}` | Text of chunk `i` |
| `GET` | `/api/books/{id}/audio/{i}` | mp3 for chunk `i` (generated + cached on first request) |
| `PATCH` | `/api/books/{id}/progress` | Update `current_chunk` |
| `PATCH` | `/api/books/{id}/settings` | Update `voice` / `rate` |
| `DELETE` | `/api/books/{id}` | Remove a book |

## Roadmap

- Android client against the existing API
- Chapter detection for EPUB (currently one flat chunk stream)
- Background pre-fetch of the next chunk's audio while the current one plays
