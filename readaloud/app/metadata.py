"""Best-effort book metadata (author/cover/genre/year) via the Open Library
search API — free, keyless. Used only to make library tiles nicer; a
failed or missing lookup just means a plain tile, never a hard error.
"""

import re

import requests

SEARCH_URL = "https://openlibrary.org/search.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
TIMEOUT = 5

GENRE_HINTS = [
    "science fiction",
    "fantasy",
    "mystery",
    "thriller",
    "horror",
    "romance",
    "biography",
    "history",
    "poetry",
    "young adult",
    "children",
    "adventure",
    "classics",
    "nonfiction",
    "fiction",
]

_NOISE = re.compile(
    r"\b(unabridged|abridged|audiobook|full cast|a novel)\b|\([^)]*\)|\[[^\]]*\]",
    re.IGNORECASE,
)


def clean_title_guess(raw_title: str) -> str:
    text = raw_title.replace("_", " ").replace("-", " ")
    text = _NOISE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def _pick_genre(subjects: list[str] | None) -> str | None:
    if not subjects:
        return None
    for subject in subjects:
        lowered = subject.lower()
        if any(hint in lowered for hint in GENRE_HINTS):
            return subject
    return subjects[0]


def lookup(title: str, author: str | None = None) -> dict | None:
    query_title = clean_title_guess(title)
    if not query_title:
        return None

    params = {
        "title": query_title,
        "limit": 1,
        "fields": "title,author_name,cover_i,first_publish_year,subject",
    }
    if author:
        params["author"] = author

    try:
        resp = requests.get(SEARCH_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        docs = resp.json().get("docs") or []
    except Exception:
        return None

    if not docs:
        return None

    doc = docs[0]
    cover_id = doc.get("cover_i")
    author_names = doc.get("author_name") or []

    return {
        "author": author_names[0] if author_names else None,
        "cover_url": COVER_URL.format(cover_id=cover_id) if cover_id else None,
        "year": doc.get("first_publish_year"),
        "genre": _pick_genre(doc.get("subject")),
    }
