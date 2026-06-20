#!/usr/bin/env python3
"""
adaptive_runtime/storage/lesson_usage_tracker.py

P3.1 Lesson Usage Tracking.

Track which memory lessons are retrieved, which are applied, and what reward follows.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LessonUsageTracker:
    def __init__(self, path: str | Path = "data/runtime/lesson_usage.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_many(
        self,
        *,
        trajectory_id: str,
        query: str,
        action: str,
        retrieved_lessons: list[dict[str, Any]],
        applied_lesson_ids: list[str],
        reward: float,
        reflection_passed: bool,
        data_source: str,
        label_confidence: float,
    ) -> int:
        applied = set(applied_lesson_ids or [])
        count = 0

        for rank, lesson in enumerate(retrieved_lessons or [], start=1):
            lesson_id = lesson.get("lesson_id") or lesson.get("task_id") or f"unknown_rank_{rank}"

            record = {
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "trajectory_id": trajectory_id,
                "query": query,
                "action": action,
                "lesson_id": lesson_id,
                "task_id": lesson.get("task_id"),
                "issue_number": lesson.get("issue_number"),
                "repo": lesson.get("repo"),
                "domain": lesson.get("domain"),
                "rank": rank,
                "retrieval_score": lesson.get("score"),
                "retrieved": True,
                "applied": lesson_id in applied or lesson.get("task_id") in applied,
                "reward": reward,
                "reflection_passed": reflection_passed,
                "data_source": data_source,
                "label_confidence": label_confidence,
            }

            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            count += 1

        return count
