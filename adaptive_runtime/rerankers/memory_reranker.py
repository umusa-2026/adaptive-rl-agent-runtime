#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def infer_query_domain(query: str) -> str:
    q = query.lower()

    if any(k in q for k in ["settings", "mcp", "llm", "config", "payload", "tavily"]):
        return "settings_configuration"

    if any(k in q for k in ["render", "ui", "frontend", "component", "viewer", "event"]):
        return "frontend_ui"

    if any(k in q for k in ["endpoint", "auth", "permission", "security", "access"]):
        return "security_endpoint"

    return "unknown"


def domain_multiplier(query_domain: str, lesson_domain: str | None) -> float:
    if query_domain == "unknown" or not lesson_domain:
        return 1.0

    if query_domain == lesson_domain:
        return 1.0

    return 0.2


class MemoryReranker:
    """
    Quality-aware memory reranker.

    Purpose:
        Convert raw retrieval ranking into self-improving memory ranking.

    Formula:
        final_score =
            retrieval_score
            + alpha * lesson_quality_score * domain_multiplier

    This is P3.3c:
        retrieve -> rerank -> select
    """

    def __init__(
        self,
        quality_path: str | Path = "data/memory/lesson_quality.json",
        alpha: float = 0.2,
    ):
        self.quality_path = Path(quality_path)
        self.alpha = alpha
        self.quality = self._load_quality()

    def _load_quality(self) -> dict[str, Any]:
        if not self.quality_path.exists():
            return {}

        return json.loads(self.quality_path.read_text(encoding="utf-8"))

    def get_quality_score(self, lesson: dict[str, Any]) -> float:
        lesson_id = lesson.get("lesson_id") or lesson.get("task_id")

        if lesson_id in self.quality:
            return float(self.quality[lesson_id].get("quality_score", 0.0))

        return 0.0

    def rerank(
        self,
        query: str,
        lessons: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        query_domain = infer_query_domain(query)

        reranked = []

        for lesson in lessons:
            retrieval_score = float(lesson.get("score", 0.0))
            quality_score = self.get_quality_score(lesson)
            lesson_domain = lesson.get("domain")

            multiplier = domain_multiplier(query_domain, lesson_domain)

            final_score = (
                retrieval_score
                + self.alpha * quality_score * multiplier
            )

            row = dict(lesson)
            row["query_domain"] = query_domain
            row["retrieval_score"] = retrieval_score
            row["quality_score"] = quality_score
            row["domain_multiplier"] = multiplier
            row["final_score"] = final_score

            reranked.append(row)

        reranked.sort(key=lambda x: x["final_score"], reverse=True)

        return reranked