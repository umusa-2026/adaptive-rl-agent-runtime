#!/usr/bin/env python3
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

class TrajectoryLogger:
    """
    JSONL trajectory logger.

    Goal:
        Save each runtime interaction as one learning trajectory.

    Output:
        data/runtime/trajectories.jsonl

    Why:
        Future bandit/RL policy will train from this file:
            state -> action -> outcome/reward
    """

    def __init__(self, path: str | Path = "data/runtime/trajectories.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, record: dict[str, Any]) -> str:
        trajectory_id = record.get("trajectory_id") or str(uuid.uuid4())
        record["trajectory_id"] = trajectory_id
        record["logged_at"] = datetime.now(timezone.utc).isoformat()

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return trajectory_id
