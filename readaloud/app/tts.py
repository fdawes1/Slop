"""edge-tts wrapper: renders a text chunk to mp3, cached on disk per (chunk, voice, rate)."""

import hashlib
from pathlib import Path

import edge_tts

VOICES = {
    "en-GB-RyanNeural": "Ryan (British male)",
    "en-GB-SoniaNeural": "Sonia (British female)",
    "en-US-GuyNeural": "Guy (US male)",
    "en-US-AriaNeural": "Aria (US female)",
    "en-IE-EmilyNeural": "Emily (Irish female)",
    "en-AU-WilliamNeural": "William (Australian male)",
}

DEFAULT_VOICE = "en-GB-RyanNeural"
DEFAULT_RATE = "+0%"


def cache_key(text: str, voice: str, rate: str) -> str:
    digest = hashlib.sha256(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()
    return digest[:24]


async def synthesize(text: str, out_path: Path, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(out_path))
