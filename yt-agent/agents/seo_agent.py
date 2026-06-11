from __future__ import annotations
import json
from typing import Dict, List
import anthropic
from models import Script, VideoMetadata, Section


_SYSTEM = """You are a YouTube SEO expert. You optimize titles, descriptions, and tags
to maximize click-through rate and discoverability. You know the YouTube algorithm deeply.
Write metadata that ranks well AND compels humans to click.
Always return valid JSON only."""


def generate_metadata(
    script: Script,
    research: Dict,
    channel_config: Dict,
    client: anthropic.Anthropic,
    model: str = "claude-haiku-4-5-20251001",
) -> VideoMetadata:
    channel_name = channel_config["channel"]["name"]
    niche = channel_config["channel"]["niche"]
    preview = (
        f"Hook: {script.hook[:300]}\n"
        f"Sections: {', '.join(s.heading for s in script.sections)}\n"
        f"CTA: {script.cta[:150]}"
    )

    prompt = f"""Create optimized YouTube metadata for this video.

Channel: {channel_name}
Niche: {niche}
Topic: {script.topic}
Angle: {script.angle}
Target keywords: {json.dumps(research.get('target_keywords', []))}

Script preview:
{preview}

Return JSON:
{{
  "title": "55-70 chars. Lead with primary keyword. Create curiosity. No ALL CAPS. No clickbait.",
  "description": "Full description. First 150 chars are critical (show in search). Structure:\\n1. Hook sentence\\n2. What they'll learn (3-4 bullets)\\n3. [TIMESTAMPS]\\n4. Subscribe CTA\\n5. Relevant hashtags\\nTarget 800-1500 chars total.",
  "tags": ["primary keyword", "secondary kw", "...", "long tail phrase"],
  "category_id": "28",
  "privacy_status": "public",
  "made_for_kids": false
}}

Generate 15-20 tags. Mix: exact match keywords, broad niche terms, long-tail variants."""

    resp = client.messages.create(
        model=model, max_tokens=2048, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    data = json.loads(text[text.find("{"):text.rfind("}") + 1])

    return VideoMetadata(
        title=data["title"],
        description=data["description"],
        tags=data["tags"],
        category_id=data.get("category_id", "28"),
        privacy_status=data.get("privacy_status", "public"),
        made_for_kids=data.get("made_for_kids", False),
    )


def add_timestamps(description: str, sections: List[Section], audio_durations: List[float]) -> str:
    if not audio_durations or "[TIMESTAMPS]" not in description:
        return description

    lines = ["0:00 - Introduction"]
    cumulative = audio_durations[0] if audio_durations else 0
    for section, duration in zip(sections, audio_durations[1:]):
        m = int(cumulative // 60)
        s = int(cumulative % 60)
        lines.append(f"{m}:{s:02d} - {section.heading}")
        cumulative += duration

    return description.replace("[TIMESTAMPS]", "\n".join(lines))
