# readaloud — handoff notes

Personal web app for Felix: drop books in, get them read aloud. Built incrementally
in one long session (2026-08-06). This file is for whichever agent picks this up next.

## Where things live

- Working copy: `~/code-server/workspace/Slop/readaloud/` (this repo is a subfolder
  of `Slop`, Felix's general "AI-generated projects" dumping-ground monorepo — it has
  ~29 other unrelated project folders in it, don't touch those).
- GitHub: pushed to `fdawes1/Slop` on `main`, NOT a standalone repo. `readaloud/` is
  just one folder in it. (We originally tried to create a standalone `fdawes1/readaloud`
  repo — failed, see "GitHub auth" gotcha below — so it lives in Slop instead.)
- Run it: `cd ~/code-server/workspace/Slop/readaloud && source .venv/bin/activate &&
  uvicorn app.main:app --host 0.0.0.0 --port 8000`. Usually run via `nohup ... &`
  with logs at `/tmp/readaloud_server.log`, restarted with `fuser -k 8000/tcp` first.
- Felix uses it live from his phone's browser over the LAN (this machine is
  `192.168.1.25`, hostname `holly`). He has been the actual QA loop all session —
  he finds bugs by using it, not by me screenshotting anything.
- **`storage/books/` currently has ~280 real book directories** — Felix bulk-uploaded
  his actual library via the folder-upload feature. This is real user data, not test
  fixtures. Don't delete it. (`storage/` is gitignored.)

## Architecture (brief — read the code for detail, it's small)

- `app/main.py` — FastAPI REST API, deliberately decoupled from the frontend so a
  future Android app could hit the same endpoints (explicitly asked for; not built).
- `app/extract.py` — text extraction (pypdf / ebooklib+BeautifulSoup) + paragraph-aware
  chunking (~1800 chars/chunk) + embedded title/author extraction from EPUB/PDF metadata.
- `app/tts.py` — edge-tts wrapper, caches rendered mp3 per (text, voice, rate) hash.
- `app/metadata.py` — Open Library Search API lookup (free, keyless) for
  author/cover/genre/year on upload. Google Books API was tried first and hit a
  429 quota-exhausted error on its shared anonymous quota — don't bother retrying
  that, Open Library works fine and is what's wired up.
- `app/cast.py` — Google Cast integration via `pychromecast`. Discovers LAN devices
  via mDNS, tells the chosen speaker to pull audio directly from this server's own
  `/api/books/{id}/audio/{index}` (not relayed through the browser). Auto-advances
  chunks via a `MediaStatusListener`.
- `static/` — vanilla HTML/CSS/JS, no build step, no framework.

## Gotchas (non-obvious, will cost time if rediscovered)

1. **mDNS/Chromecast discovery needs the Bash sandbox disabled** to test from a
   shell (`dangerouslyDisableSandbox: true` on the Bash tool call) — the sandboxed
   shell blocks multicast, so `pychromecast.get_chromecasts()` returns 0 devices
   when run through a normal sandboxed command. This only affects *my* dev/test
   commands — the always-running server process works fine for Felix's real usage
   once it's up.
2. mDNS discovery is inherently flaky (UDP, no delivery guarantee) — found 8 devices
   once, 1 on a retry, 0 on another, all in the same few minutes. That's normal
   Chromecast behavior, not a bug. `DISCOVERY_TIMEOUT` in `cast.py` is 10s.
3. **No FTP server on this box.** Felix tried FileZilla over FTP to bulk-copy books
   in; redirect that instinct to either SFTP (port 22, his password auth works fine)
   or — better — the app's own folder-upload feature, which is what he ended up using.
4. **`gh` is authed as `fdawes1` via a fine-grained PAT that cannot create new repos**
   (`gh repo create` and `POST /user/repos` both 403 "Resource not accessible").
   That's why this lives inside `Slop` rather than its own repo. Don't waste time
   retrying repo creation with this token.
5. Local git identity (`user.name`/`user.email`) had to be set per-repo inside `Slop`
   — there was no global git identity on this machine. Don't set it globally.
6. Server has no `--reload` in the usual invocation — restart manually after editing
   any `app/*.py` file (`fuser -k 8000/tcp` then relaunch; sometimes needs a retry/sleep
   due to graceful-shutdown timing).

## Bugs fixed this session (check these first if symptoms resurface)

- EPUB extraction crashed on *every* upload — `ebooklib.epub` has no `ITEM_DOCUMENT`
  attribute, it's `ebooklib.ITEM_DOCUMENT` on the package root.
- Swapping the sort `<select>` for buttons left a dangling `sortSelect` JS reference
  that threw on page load and killed the whole script before `loadLibrary()` ran —
  looked exactly like "my uploaded books vanished," but they were safe on disk the
  whole time. If the library ever renders blank again, check the browser console
  for a JS error first, before assuming data loss.
- Confirm-delete modal used `display: flex` unconditionally in CSS, which fought the
  `hidden` attribute — Cancel/Delete couldn't actually close it. Fixed via
  `.modal-overlay:not([hidden])`.
- `cast.py` had an inconsistent locking pattern: `start_cast` called `stop_cast` while
  holding `_lock`, but the public API endpoint called `stop_cast` directly with no
  lock — a real race condition. Fixed with an internal `_stop_cast_locked` + a
  locking public `stop_cast` wrapper.
- The auto-advance `MediaStatusListener` could throw unhandled in a background
  pychromecast thread if a book was deleted mid-cast (`load_meta` raises `HTTPException`
  outside any request context). Now caught.
- The upload-progress-bar UI update overwrote `dropzone.innerHTML`, which destroyed
  the hidden `<input>` elements that were nested inside it — "choose a folder" broke
  permanently after the very first upload of the session. Fixed by moving those
  inputs to be siblings of `#dropzone`, not children.
- Missing error handling on the "stop cast" button, and local playback wasn't
  re-primed after stopping a cast (hit play, nothing happened). Both fixed.

## Feature set as of now

- Upload: `.txt`/`.pdf`/`.epub` (TTS-narrated, chunked) or `.mp3`/`.m4a`/`.m4b`
  (played directly, no TTS). Drag-and-drop of files or whole folders (recursive
  via `webkitGetAsEntry`), or click-to-choose.
- Per-book voice + speed (edge-tts, 6 curated voices), resumable progress.
- Cast to Google Home/Chromecast, auto-advancing chunks on the speaker itself.
- Library: grid tiles with cover/author/genre from Open Library, search box, sort
  buttons (recent/title/author/in-progress), filter chips for reading status
  (not started/in progress/finished) and readout type (TTS vs audiobook), genre chips.
- Toasts + a custom confirm modal (replaced native `alert`/`confirm`).
- Sticky bottom player bar so playback controls stay visible while scrolling text.

## Explicitly not done / deferred

- Android client (API's shaped for one, nothing built).
- EPUB chapter detection (one flat chunk stream per book currently).
- No UI to manually correct wrong/missing metadata (author/cover/genre).
- Desktop layout for the sticky player bar is a minor cosmetic compromise (a
  negative-margin trick only breaks fully out to the viewport edge on narrow/mobile
  screens). Mobile is the actual target usage, so this hasn't been chased further.
- Nothing in this app has been visually verified via a browser/screenshot tool by
  the agent — Felix testing live on his phone has been the QA loop all session.
  Ask him to check in-browser after further UI changes rather than assuming it's fine.
