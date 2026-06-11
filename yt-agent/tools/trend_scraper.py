from __future__ import annotations
from typing import List, Dict


def get_google_trends(keywords: List[str], timeframe: str = "now 7-d") -> Dict[str, List]:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload(keywords[:5], timeframe=timeframe, geo="US")
        interest = pytrends.interest_over_time()
        if interest.empty:
            return {}
        return {col: interest[col].tolist() for col in interest.columns if col != "isPartial"}
    except Exception:
        return {}


def get_rising_queries(keyword: str) -> List[str]:
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload([keyword], timeframe="now 7-d", geo="US")
        related = pytrends.related_queries()
        rising = related.get(keyword, {}).get("rising")
        if rising is not None and not rising.empty:
            return rising["query"].head(10).tolist()
        return []
    except Exception:
        return []


def search_youtube_videos(query: str, max_results: int = 10) -> List[Dict]:
    try:
        import yt_dlp
        opts = {"quiet": True, "extract_flat": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            entries = results.get("entries", [])
            return [
                {
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "view_count": e.get("view_count", 0),
                    "duration": e.get("duration", 0),
                    "uploader": e.get("uploader"),
                }
                for e in entries if e
            ]
    except Exception:
        return []
