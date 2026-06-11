from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict


def refresh_analytics(env: Dict, data_dir: str = "data") -> List[Dict]:
    from tools.youtube_api import get_youtube_client, get_video_analytics

    history_path = Path(data_dir) / "video_history.json"
    if not history_path.exists():
        return []

    history = json.loads(history_path.read_text())
    if not history:
        return []

    try:
        youtube = get_youtube_client()
        for record in history:
            if not record.get("youtube_id"):
                continue
            stats = get_video_analytics(youtube, record["youtube_id"])
            if stats:
                record.update({
                    "views": stats.get("views", record.get("views", 0)),
                    "likes": stats.get("likes", record.get("likes", 0)),
                    "comments": stats.get("comments", record.get("comments", 0)),
                    "last_updated": datetime.now().isoformat(),
                })
        history_path.write_text(json.dumps(history, indent=2))
    except Exception as e:
        print(f"Analytics refresh error: {e}")

    return history


def get_performance_summary(data_dir: str = "data") -> Dict:
    history_path = Path(data_dir) / "video_history.json"
    if not history_path.exists():
        return {"total_videos": 0, "total_views": 0, "avg_views": 0, "top_videos": [], "last_upload": None}

    history = json.loads(history_path.read_text())
    if not history:
        return {"total_videos": 0, "total_views": 0, "avg_views": 0, "top_videos": [], "last_upload": None}

    total_views = sum(v.get("views", 0) for v in history)
    top = sorted(history, key=lambda v: v.get("views", 0), reverse=True)[:5]

    return {
        "total_videos": len(history),
        "total_views": total_views,
        "avg_views": total_views // len(history),
        "top_videos": [{"title": v["title"], "views": v["views"], "id": v.get("youtube_id")} for v in top],
        "last_upload": history[-1].get("published_at"),
    }
