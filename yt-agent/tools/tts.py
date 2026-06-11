from __future__ import annotations
import asyncio
from typing import Dict


async def _edge_tts_async(text: str, output_path: str, voice: str, speed: str) -> str:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_path)
    return output_path


def synthesize_edge_tts(text: str, output_path: str, voice: str, speed: str = "+5%") -> str:
    return asyncio.run(_edge_tts_async(text, output_path, voice, speed))


def synthesize_elevenlabs(text: str, output_path: str, voice_id: str, api_key: str) -> str:
    import requests
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.8},
    }
    r = requests.post(url, json=payload, headers=headers)
    r.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(r.content)
    return output_path


def synthesize_openai_tts(text: str, output_path: str, voice: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    with client.audio.speech.with_streaming_response.create(
        model="tts-1-hd",
        voice=voice,
        input=text,
    ) as response:
        response.stream_to_file(output_path)
    return output_path


def get_audio_duration(path: str) -> float:
    from moviepy.editor import AudioFileClip
    with AudioFileClip(path) as audio:
        return audio.duration


def synthesize(text: str, output_path: str, settings: Dict, env: Dict) -> str:
    provider = settings.get("provider", "edge-tts")

    if provider == "elevenlabs":
        return synthesize_elevenlabs(
            text, output_path,
            voice_id=env.get("ELEVENLABS_VOICE_ID", ""),
            api_key=env.get("ELEVENLABS_API_KEY", ""),
        )
    elif provider == "openai":
        return synthesize_openai_tts(
            text, output_path,
            voice=settings.get("voice", "onyx"),
            api_key=env.get("OPENAI_API_KEY", ""),
        )
    else:
        return synthesize_edge_tts(
            text, output_path,
            voice=settings.get("voice", "en-US-AndrewNeural"),
            speed=settings.get("speed", "+5%"),
        )
