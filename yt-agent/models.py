from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import uuid


@dataclass
class Section:
    heading: str
    narration: str
    visual_prompt: str
    b_roll_keywords: List[str] = field(default_factory=list)
    duration_estimate: float = 30.0
    audio_path: Optional[str] = None
    image_path: Optional[str] = None


@dataclass
class Script:
    topic: str
    angle: str
    hook: str
    sections: List[Section]
    cta: str
    total_duration: float = 0.0

    def full_narration(self) -> str:
        parts = [self.hook] + [s.narration for s in self.sections] + [self.cta]
        return "\n\n".join(parts)

    def section_narrations(self) -> List[str]:
        return [self.hook] + [s.narration for s in self.sections] + [self.cta]


@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: List[str]
    category_id: str = "28"
    privacy_status: str = "public"
    made_for_kids: bool = False
    scheduled_publish_at: Optional[str] = None


@dataclass
class VideoRecord:
    run_id: str
    topic: str
    youtube_id: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    ctr: float = 0.0
    avg_view_duration: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PipelineState:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    angle: str = ""
    status: str = "initialized"
    script: Optional[dict] = None
    metadata: Optional[dict] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    youtube_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PipelineState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
