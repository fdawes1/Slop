from __future__ import annotations
import json
from typing import Dict
import anthropic
from models import Script, Section


_SYSTEM = """You are an elite YouTube scriptwriter. You write engaging, educational scripts
that hold attention from first second to last. Your scripts have:
- Irresistible hooks that open a curiosity gap in the first 30 seconds
- Clean structure with smooth section transitions
- Conversational but authoritative tone — like a knowledgeable friend
- Pattern interrupts every 60-90 seconds (stat drop, rhetorical question, callback)
- Strategic CTAs woven in naturally
You write for voiceover narration — conversational, not academic. No headers in the narration.
Always return valid JSON only."""


def generate_script(
    topic: str,
    angle: str,
    research: Dict,
    channel_config: Dict,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
    target_duration: int = 600,
) -> Script:
    tone = channel_config["channel"]["tone"]
    audience = channel_config["channel"]["target_audience"]
    sections_count = channel_config["channel"]["video_format"]["sections_count"]

    words_per_minute = 148
    target_words = int((target_duration / 60) * words_per_minute)
    words_per_section = target_words // (sections_count + 2)

    prompt = f"""Write a complete, publish-ready YouTube script.

Topic: {topic}
Angle: {angle}
Tone: {tone}
Target audience: {audience}
Target duration: {target_duration}s (~{target_words} words total)
Words per section: ~{words_per_section} words

Research:
{json.dumps(research, indent=2)}

Return this exact JSON structure:
{{
  "topic": "{topic}",
  "angle": "{angle}",
  "hook": "First 30-45 seconds. Open a curiosity gap. Drop a shocking stat or counterintuitive claim immediately. DO NOT start with 'Hey guys' or 'Welcome back'. ~{words_per_section // 2} words. FULLY WRITTEN.",
  "sections": [
    {{
      "heading": "Internal section label (not spoken)",
      "narration": "Full spoken narration for this section. Conversational. Include a pattern interrupt (rhetorical question, stat, callback). ~{words_per_section} words. FULLY WRITTEN — not a summary.",
      "visual_prompt": "Detailed DALL-E 3 prompt for a cinematic still image illustrating this section. Specify: subject, composition, lighting style, color palette, mood, camera angle. No text in image.",
      "b_roll_keywords": ["search term 1", "search term 2", "search term 3"],
      "duration_estimate": 90.0
    }}
  ],
  "cta": "Final 20-30 seconds. Naturally ask for subscribe + like. Tease what's coming next. Leave on a cliffhanger or thought-provoking question. ~{words_per_section // 3} words. FULLY WRITTEN."
}}

Write EXACTLY {sections_count} sections. Every narration must be fully written out prose — not bullet points, not placeholders."""

    resp = client.messages.create(
        model=model, max_tokens=8096, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    data = json.loads(text[text.find("{"):text.rfind("}") + 1])

    sections = [
        Section(
            heading=s["heading"],
            narration=s["narration"],
            visual_prompt=s["visual_prompt"],
            b_roll_keywords=s.get("b_roll_keywords", []),
            duration_estimate=s.get("duration_estimate", 90.0),
        )
        for s in data["sections"]
    ]

    return Script(
        topic=data["topic"],
        angle=data["angle"],
        hook=data["hook"],
        sections=sections,
        cta=data["cta"],
        total_duration=sum(s.duration_estimate for s in sections) + 60,
    )
