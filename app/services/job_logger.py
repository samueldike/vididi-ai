from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobLogger:
    def __init__(self, job_id: str, job_dir: Path) -> None:
        self.job_id = job_id
        self.job_dir = job_dir
        self.log_path = job_dir / "job.log.jsonl"
        self.meta_path = job_dir / "job.meta.json"
        self.events: list[dict[str, Any]] = []

    def event(self, stage: str, message: str, **data: Any) -> None:
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_id": self.job_id,
            "stage": stage,
            "message": message,
            "data": data,
        }
        self.events.append(row)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def write_meta(self, **meta: Any) -> None:
        self.meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

