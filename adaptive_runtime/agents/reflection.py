#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re

@dataclass
class ReflectionReport:
    passed: bool
    score: float
    missing_items: list[str]
    risks: list[str]
    recommendations: list[str]
    applied_lessons: list[str]
    checked_files: list[str]

class ReflectionAgent:
    def __init__(self, min_score_to_pass: float = 0.75):
        self.min_score_to_pass = min_score_to_pass

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[A-Za-z][A-Za-z0-9_/-]{2,}", (text or "").lower()))

    @staticmethod
    def _contains_any(text: str, keywords: list[str]) -> bool:
        t = (text or "").lower()
        return any(k.lower() in t for k in keywords)

    def _lesson_keywords_used(self, draft: str, lessons: list[dict[str, Any]]) -> list[str]:
        used = []
        draft_tokens = self._tokens(draft)
        for lesson in lessons:
            lesson_tokens = self._tokens(lesson.get("lesson", ""))
            if len(draft_tokens & lesson_tokens) >= 5:
                used.append(lesson.get("task_id", "unknown"))
        return used

    def _evidence_files_mentioned(self, draft: str, lessons: list[dict[str, Any]]) -> list[str]:
        mentioned = []
        draft_lower = (draft or "").lower()
        for lesson in lessons:
            files = lesson.get("evidence", {}).get("changed_files", []) or []
            for f in files[:10]:
                basename = f.split("/")[-1].lower()
                if f.lower() in draft_lower or basename in draft_lower:
                    mentioned.append(f)
        seen, out = set(), []
        for f in mentioned:
            if f not in seen:
                seen.add(f)
                out.append(f)
        return out

    def reflect(self, query: str, draft_answer: str, planner_decision: dict[str, Any], retrieved_lessons: list[dict[str, Any]]) -> ReflectionReport:
        missing, risks, recs = [], [], []
        need_memory = planner_decision.get("need_memory", False)
        need_file_inspection = planner_decision.get("need_file_inspection", False)

        applied_lessons = self._lesson_keywords_used(draft_answer, retrieved_lessons)
        checked_files = self._evidence_files_mentioned(draft_answer, retrieved_lessons)

        if need_memory and not applied_lessons:
            missing.append("retrieved_lesson_not_applied")
            recs.append("Explicitly apply the top retrieved lesson to the proposed solution.")
            risks.append("The answer may repeat a previously observed failure pattern.")

        if need_file_inspection and not checked_files:
            missing.append("evidence_files_not_mentioned")
            recs.append("Mention which files/components should be inspected or modified.")
            risks.append("The answer may be too abstract and not actionable in the codebase.")

        if self._contains_any(query, ["bug", "lost", "reset", "render", "event", "endpoint", "settings"]):
            if not self._contains_any(draft_answer, ["test", "regression", "typecheck", "lint", "pytest", "vitest", "validation"]):
                missing.append("validation_plan_missing")
                recs.append("Add a validation plan: targeted test, regression test, typecheck, lint, or manual verification.")
                risks.append("The solution may not be verifiable or regression-safe.")

        if self._contains_any(query, ["settings", "mcp", "llm", "tavily", "basic", "advanced"]):
            if not self._contains_any(draft_answer, ["ownership", "payload", "preserve", "scope", "owned", "section", "mcp_config"]):
                missing.append("settings_ownership_constraint_missing")
                recs.append("For settings bugs, discuss ownership boundaries and scoped save payloads.")
                risks.append("A save handler may accidentally overwrite unrelated settings.")

        if self._contains_any(query, ["render", "event", "tool call", "viewer", "acp"]):
            if not self._contains_any(draft_answer, ["pipeline", "type guard", "event", "component", "i18n", "test"]):
                missing.append("frontend_event_pipeline_missing")
                recs.append("For frontend event rendering, trace type definitions, type guards, event conversion, content helpers, components, i18n, and tests.")
                risks.append("The answer may add a component without integrating the full event rendering pipeline.")

        score = 1.0 - 0.18 * len(missing) - 0.08 * len(risks)
        score = max(0.0, min(1.0, score))
        return ReflectionReport(
            passed=score >= self.min_score_to_pass,
            score=round(score, 3),
            missing_items=missing,
            risks=risks,
            recommendations=recs,
            applied_lessons=applied_lessons,
            checked_files=checked_files,
        )

    @staticmethod
    def to_dict(report: ReflectionReport) -> dict[str, Any]:
        return asdict(report)
