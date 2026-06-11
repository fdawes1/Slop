from __future__ import annotations
import json
from pathlib import Path
from typing import Optional, List
from models import PipelineState


def save_state(state: PipelineState, data_dir: str = "data"):
    path = Path(data_dir) / "runs" / f"{state.run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_dict(), indent=2))


def load_state(run_id: str, data_dir: str = "data") -> Optional[PipelineState]:
    path = Path(data_dir) / "runs" / f"{run_id}.json"
    if not path.exists():
        return None
    return PipelineState.from_dict(json.loads(path.read_text()))


def list_runs(data_dir: str = "data") -> List[dict]:
    runs_dir = Path(data_dir) / "runs"
    if not runs_dir.exists():
        return []
    runs = []
    for f in sorted(runs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(f.read_text())
            runs.append({
                "run_id": d["run_id"],
                "topic": d.get("topic", ""),
                "status": d.get("status", ""),
                "created_at": d.get("created_at", ""),
                "youtube_id": d.get("youtube_id"),
            })
        except Exception:
            pass
    return runs
