from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from models import VideoMetadata, VideoRecord


def upload_video(
    video_path: str,
    thumbnail_path: Optional[str],
    metadata: VideoMetadata,
    env: Dict,
    data_dir: str = "data",
) -> str:
    from tools.youtube_api import get_youtube_client, upload_video as yt_upload

    secrets = "client_secrets.json"
    youtube = get_youtube_client(secrets if Path(secrets).exists() else None)

    return yt_upload(
        youtube=youtube,
        video_path=video_path,
        title=metadata.title,
        description=metadata.description,
        tags=metadata.tags,
        category_id=metadata.category_id,
        privacy_status=metadata.privacy_status,
        made_for_kids=metadata.made_for_kids,
        thumbnail_path=thumbnail_path,
        scheduled_publish_at=metadata.scheduled_publish_at,
    )


def save_video_record(
    run_id: str,
    topic: str,
    metadata: VideoMetadata,
    youtube_id: str,
    data_dir: str = "data",
):
    history_path = Path(data_dir) / "video_history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []

    history.append({
        "run_id": run_id,
        "topic": topic,
        "youtube_id": youtube_id,
        "title": metadata.title,
        "published_at": datetime.now().isoformat(),
        "views": 0,
        "likes": 0,
        "comments": 0,
        "ctr": 0.0,
    })

    history_path.write_text(json.dumps(history, indent=2))
