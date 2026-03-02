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
        self.status_path = job_dir / "job.status.json"
        self.result_path = job_dir / "job.result.json"
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

    def write_status(self, status: str, **data: Any) -> None:
        payload = {
            "job_id": self.job_id,
            "status": status,
            **data,
        }
        self.status_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def write_result(self, result: dict[str, Any]) -> None:
        self.result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
