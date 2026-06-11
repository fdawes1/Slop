from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
from models import Script


def generate_voiceover(
    script: Script,
    run_id: str,
    tts_settings: Dict,
    env: Dict,
    output_dir: str = "output",
) -> Tuple[str, List[float]]:
    from tools.tts import synthesize, get_audio_duration
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    audio_dir = Path(output_dir) / run_id / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    narrations = script.section_narrations()
    audio_files: List[str] = []
    durations: List[float] = []

    for i, narration in enumerate(narrations):
        path = str(audio_dir / f"section_{i:02d}.mp3")
        synthesize(narration, path, tts_settings, env)
        duration = get_audio_duration(path)
        audio_files.append(path)
        durations.append(duration)

    combined_path = str(Path(output_dir) / run_id / "voiceover.mp3")
    clips = [AudioFileClip(f) for f in audio_files]
    combined = concatenate_audioclips(clips)
    combined.write_audiofile(combined_path, verbose=False, logger=None)
    for c in clips:
        c.close()
    combined.close()

    return combined_path, durations
