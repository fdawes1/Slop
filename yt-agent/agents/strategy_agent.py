from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict
import anthropic


_SYSTEM = """You are a YouTube channel strategist AI. You analyze channel performance,
identify content opportunities, and maintain content calendars for maximum growth.
You understand the YouTube algorithm, audience psychology, and viral content mechanics.
Always respond with valid JSON only — no markdown, no explanation."""


def select_topic(
    trending_topics: List[Dict],
    channel_config: Dict,
    history: List[Dict],
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> Dict:
    recent = [v.get("topic", "") for v in history[-20:]]
    prompt = f"""Select the BEST topic for the next YouTube video.

Channel niche: {channel_config['channel']['niche']}
Target audience: {channel_config['channel']['target_audience']}
Content pillars: {json.dumps(channel_config['channel']['content_pillars'])}
Recently published (avoid repeating): {json.dumps(recent)}

Trending topic data:
{json.dumps(trending_topics, indent=2)}

Return JSON:
{{
  "topic": "the specific topic",
  "angle": "the unique perspective that makes this video stand out from existing content",
  "reasoning": "why this will perform well right now",
  "estimated_search_volume": "high|medium|low",
  "competition_level": "high|medium|low",
  "viral_potential": "high|medium|low"
}}"""

    resp = client.messages.create(
        model=model, max_tokens=1024, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(resp.content[0].text)


def generate_content_calendar(
    channel_config: Dict,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
    days: int = 7,
) -> List[Dict]:
    prompt = f"""Create a {days}-day content calendar for this YouTube channel.

Channel: {channel_config['channel']['name']}
Niche: {channel_config['channel']['niche']}
Content pillars: {json.dumps(channel_config['channel']['content_pillars'])}
Upload schedule: {json.dumps(channel_config['channel']['upload_schedule'])}

Generate {days} video ideas that complement each other and build channel authority over time.
Vary the content pillar each day. Mix evergreen and trending topics.

Return a JSON array of {days} objects:
[{{
  "day": 1,
  "topic": "specific topic",
  "angle": "unique angle",
  "pillar": "which content pillar",
  "target_keywords": ["keyword1", "keyword2"],
  "estimated_title": "working title under 65 chars",
  "content_type": "explainer|news|tutorial|opinion|listicle"
}}]"""

    resp = client.messages.create(
        model=model, max_tokens=3000, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    return json.loads(text[text.find("["):text.rfind("]") + 1])


def analyze_performance(
    history: List[Dict],
    channel_config: Dict,
    client: anthropic.Anthropic,
    model: str = "claude-haiku-4-5-20251001",
) -> Dict:
    if not history:
        return {"insights": [], "recommendations": []}

    prompt = f"""Analyze this YouTube channel's performance data and extract actionable insights.

Channel niche: {channel_config['channel']['niche']}
Performance data (last {min(len(history), 30)} videos):
{json.dumps(history[-30:], indent=2)}

Return JSON:
{{
  "top_performing_themes": ["theme1", "theme2"],
  "underperforming_themes": ["theme1"],
  "optimal_title_patterns": ["pattern1", "pattern2"],
  "best_upload_days": ["Monday", "Wednesday"],
  "avg_views": 0,
  "insights": ["actionable insight 1", "actionable insight 2"],
  "recommendations": ["specific recommendation 1", "specific recommendation 2"]
}}"""

    resp = client.messages.create(
        model=model, max_tokens=1024, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(resp.content[0].text)
