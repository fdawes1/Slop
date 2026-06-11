from __future__ import annotations
import pickle
from pathlib import Path
from typing import Optional, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

TOKEN_PATH = Path("data/youtube_token.pkl")


def get_youtube_client(client_secrets_file: Optional[str] = None):
    creds = None
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif not creds or not creds.valid:
        if client_secrets_file and Path(client_secrets_file).exists():
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        else:
            raise RuntimeError(
                "No valid YouTube credentials.\n"
                "1. Download client_secrets.json from Google Cloud Console\n"
                "2. Run: python run.py auth"
            )
        TOKEN_PATH.parent.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(
    youtube,
    video_path: str,
    title: str,
    description: str,
    tags: list,
    category_id: str = "28",
    privacy_status: str = "public",
    made_for_kids: bool = False,
    thumbnail_path: Optional[str] = None,
    scheduled_publish_at: Optional[str] = None,
) -> str:
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "private" if scheduled_publish_at else privacy_status,
            "madeForKids": made_for_kids,
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }
    if scheduled_publish_at:
        body["status"]["publishAt"] = scheduled_publish_at

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload {int(status.progress() * 100)}%", end="\r")

    video_id = response["id"]
    print(f"\n  Uploaded: https://youtu.be/{video_id}")

    if thumbnail_path and Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path),
        ).execute()

    return video_id


def get_video_analytics(youtube, video_id: str) -> Dict[str, Any]:
    response = youtube.videos().list(
        part="statistics,contentDetails",
        id=video_id,
    ).execute()
    if not response.get("items"):
        return {}
    item = response["items"][0]
    stats = item.get("statistics", {})
    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "duration": item.get("contentDetails", {}).get("duration", ""),
    }
