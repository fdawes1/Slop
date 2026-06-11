from __future__ import annotations
import json
from typing import List, Dict
import anthropic
from tools.trend_scraper import get_rising_queries, search_youtube_videos


_SYSTEM = """You are a YouTube content research specialist. You surface the best content
opportunities by analyzing trends, competitor content, and audience interests.
Always return valid JSON only."""


def gather_trending_topics(channel_config: Dict, max_topics: int = 20) -> List[Dict]:
    seed_keywords = channel_config["channel"]["seo"]["seed_keywords"]
    topics = []

    for keyword in seed_keywords[:3]:
        for q in get_rising_queries(keyword)[:5]:
            topics.append({"source": "google_trends_rising", "query": q, "seed": keyword})

    for keyword in seed_keywords[:2]:
        for v in search_youtube_videos(f"{keyword} 2024", max_results=5):
            if v.get("view_count", 0) > 10000:
                topics.append({
                    "source": "youtube_search",
                    "query": v.get("title", ""),
                    "view_count": v.get("view_count", 0),
                    "seed": keyword,
                })

    if not topics:
        for kw in seed_keywords[:5]:
            topics.append({"source": "seed_keyword", "query": kw, "seed": kw})

    return topics[:max_topics]


def deep_research(
    topic: str,
    angle: str,
    client: anthropic.Anthropic,
    model: str = "claude-sonnet-4-6",
) -> Dict:
    related_videos = search_youtube_videos(topic, max_results=8)

    prompt = f"""Research this YouTube video topic thoroughly. Provide structured data for script writing.

Topic: {topic}
Angle: {angle}

Existing YouTube videos on this topic:
{json.dumps(related_videos, indent=2)}

Return JSON:
{{
  "key_facts": ["fact1", "fact2", "fact3", "fact4", "fact5"],
  "surprising_angles": ["surprising angle 1", "surprising angle 2"],
  "common_misconceptions": ["misconception 1", "misconception 2"],
  "section_topics": [
    {{
      "heading": "Section heading",
      "key_points": ["point 1", "point 2", "point 3"],
      "data_to_include": "specific stats, dates, names, or examples to make this section concrete"
    }},
    {{"heading": "Section 2", "key_points": [], "data_to_include": ""}},
    {{"heading": "Section 3", "key_points": [], "data_to_include": ""}},
    {{"heading": "Section 4", "key_points": [], "data_to_include": ""}},
    {{"heading": "Section 5", "key_points": [], "data_to_include": ""}}
  ],
  "hook_ideas": ["hook idea 1", "hook idea 2", "hook idea 3"],
  "cta_ideas": ["cta 1", "cta 2"],
  "competitor_gaps": ["what existing videos miss that we can cover"],
  "target_keywords": ["primary kw", "secondary kw 1", "secondary kw 2", "long tail 1", "long tail 2"]
}}"""

    resp = client.messages.create(
        model=model, max_tokens=3000, system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text
    return json.loads(text[text.find("{"):text.rfind("}") + 1])
