"""Plain-text extraction from uploaded book files, then chunking for TTS."""

import re
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub
from pypdf import PdfReader

CHUNK_TARGET_CHARS = 1800


def extract_text(path: Path, suffix: str) -> str:
    suffix = suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        return _extract_pdf(path)
    if suffix == ".epub":
        return _extract_epub(path)
    raise ValueError(f"unsupported file type: {suffix}")


def _extract_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_epub(path: Path) -> str:
    book = epub.read_epub(str(path))
    parts = []
    for item in book.get_items_of_type(epub.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n")
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def chunk_text(text: str, target_chars: int = CHUNK_TARGET_CHARS) -> list[str]:
    """Split into paragraph-aware chunks small enough for a single TTS call."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > target_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
        while len(current) > target_chars * 2:
            chunks.append(current[:target_chars])
            current = current[target_chars:]
    if current:
        chunks.append(current)

    return chunks or [""]
