#!/usr/bin/env python3
"""
adaptive_runtime/storage/lesson_usage_tracker.py

P3.1 Lesson Usage Tracking

Tracks which lessons were:
- retrieved
- raw-applied by the reflection heuristic
- domain-compatible with the query
- finally counted as applied
- associated with reward / reflection outcome

This supports later:
- P3.2 lesson quality scoring
- P3.3 quality-aware memory reranking
- P3.4 failure / attribution analysis
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from adaptive_runtime.rerankers.memory_reranker import infer_query_domain


def is_domain_compatible(
    query_domain: str | None,
    lesson_domain: str | None,
) -> bool:
    """
    Decide whether a lesson's domain is compatible with the query domain.

    MVP rule:
        - unknown query domain: allow
        - missing lesson domain: allow
        - same domain: allow
        - different domain: reject

    This prevents wrong-domain lessons from getting applied credit.
    """

    if not query_domain or query_domain == "unknown":
        return True

    if not lesson_domain:
        return True

    return query_domain == lesson_domain


class LessonUsageTracker:
    """
    Log lesson usage events to JSONL.

    One retrieved lesson produces one usage event.

    Output:
        data/runtime/lesson_usage.jsonl
    """

    def __init__(
        self,
        path: str | Path = "data/runtime/lesson_usage.jsonl",
    ):
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
        """
        Log usage records for all retrieved lessons.

        Important distinction:

        raw_applied:
            The reflection heuristic believed the lesson was applied.

        domain_compatible:
            The lesson's domain is compatible with the query domain.

        applied:
            raw_applied AND domain_compatible

        This prevents cross-domain false positives from poisoning lesson quality.
        """

        applied = set(applied_lesson_ids or [])
        query_domain = infer_query_domain(query)

        count = 0

        for rank, lesson in enumerate(retrieved_lessons or [], start=1):
            lesson_id = (
                lesson.get("lesson_id")
                or lesson.get("task_id")
                or f"unknown_rank_{rank}"
            )

            task_id = lesson.get("task_id")
            lesson_domain = lesson.get("domain")

            raw_applied = lesson_id in applied or task_id in applied
            domain_ok = is_domain_compatible(
                query_domain=query_domain,
                lesson_domain=lesson_domain,
            )

            final_applied = raw_applied and domain_ok

            record = {
                "logged_at": datetime.now(timezone.utc).isoformat(),
                "trajectory_id": trajectory_id,
                "query": query,
                "query_domain": query_domain,
                "action": action,
                "lesson_id": lesson_id,
                "task_id": task_id,
                "issue_number": lesson.get("issue_number"),
                "repo": lesson.get("repo"),
                "domain": lesson_domain,
                "rank": rank,
                "retrieval_score": lesson.get("score"),
                "retrieved": True,
                "raw_applied": raw_applied,
                "domain_compatible": domain_ok,
                "applied": final_applied,
                "reward": reward,
                "reflection_passed": reflection_passed,
                "data_source": data_source,
                "label_confidence": label_confidence,
            }

            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

            count += 1

        return count