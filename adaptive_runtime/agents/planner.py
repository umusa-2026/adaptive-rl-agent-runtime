#!/usr/bin/env python3
"""
adaptive_runtime/agents/planner.py

Planner Agent for Adaptive Coding Runtime.

Goal:
    Decide the next runtime path for a coding-agent task.

Input:
    - user query / issue / coding task
    - retrieved memory lessons

Output:
    - runtime decision:
        direct
        memory_only
        memory_then_reflection
        ask_clarification
        inspect_files_then_reflect

Why:
    This is the first policy layer before RL/bandit.
    For MVP, it is rule-based and transparent.
    Later, the Bandit/RL policy will learn these decisions from reward signals.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re


@dataclass
class PlannerDecision:
    action: str
    need_memory: bool
    need_reflection: bool
    need_file_inspection: bool
    ask_clarification: bool
    confidence: float
    reasons: list[str]
    retrieved_lesson_count: int
    top_memory_score: float


class PlannerAgent:
    """
    Rule-based Planner Agent.

    This is deliberately simple:
      - deterministic
      - explainable
      - no LLM
      - no cloud API

    Later, this rule-based planner becomes the baseline policy.
    """

    def __init__(
        self,
        memory_score_threshold: float = 3.0,
        high_memory_score_threshold: float = 7.0,
    ):
        self.memory_score_threshold = memory_score_threshold
        self.high_memory_score_threshold = high_memory_score_threshold

    def _is_unclear(self, query: str) -> bool:
        words = re.findall(r"[A-Za-z0-9_/-]+", query)
        if len(words) < 5:
            return True
        vague_terms = ["help", "fix it", "not working", "broken", "issue", "problem"]
        q = query.lower()
        return any(t in q for t in vague_terms) and len(words) < 12

    def _looks_like_bug_or_debug(self, query: str) -> bool:
        q = query.lower()
        return any(k in q for k in [
            "bug", "error", "failed", "failure", "exception", "traceback",
            "lost", "reset", "broken", "not working", "bad gateway", "500",
        ])

    def _looks_like_ui_or_event(self, query: str) -> bool:
        q = query.lower()
        return any(k in q for k in [
            "ui", "frontend", "render", "viewer", "component", "event", "tool call",
            "settings page", "tsx", "react",
        ])

    def _looks_like_security_or_endpoint(self, query: str) -> bool:
        q = query.lower()
        return any(k in q for k in [
            "endpoint", "auth", "authenticated", "permission", "security",
            "enumeration", "access", "api",
        ])

    def decide(self, query: str, retrieved_lessons: list[dict[str, Any]]) -> PlannerDecision:
        reasons: list[str] = []
        top_score = retrieved_lessons[0]["score"] if retrieved_lessons else 0.0

        need_memory = bool(retrieved_lessons and top_score >= self.memory_score_threshold)
        need_reflection = False
        need_file_inspection = False
        ask_clarification = False

        if self._is_unclear(query):
            ask_clarification = True
            reasons.append("query_is_short_or_vague")

        if need_memory:
            reasons.append(f"memory_score_above_threshold:{top_score}")

        if self._looks_like_bug_or_debug(query):
            need_reflection = True
            reasons.append("bug_or_debug_task_requires_reflection")

        if self._looks_like_ui_or_event(query):
            need_file_inspection = True
            need_reflection = True
            reasons.append("ui_or_event_task_requires_file_inspection")

        if self._looks_like_security_or_endpoint(query):
            need_file_inspection = True
            need_reflection = True
            reasons.append("security_or_endpoint_task_requires_extra_validation")

        if top_score >= self.high_memory_score_threshold:
            need_reflection = True
            reasons.append("strong_memory_match_should_be_applied_and_checked")

        # Decide final action.
        if ask_clarification and not need_memory:
            action = "ask_clarification"
            confidence = 0.55
        elif need_memory and need_file_inspection:
            action = "inspect_files_then_reflect"
            confidence = 0.85
        elif need_memory and need_reflection:
            action = "memory_then_reflection"
            confidence = 0.8
        elif need_memory:
            action = "memory_only"
            confidence = 0.7
        elif need_reflection:
            action = "reflection_only"
            confidence = 0.65
        else:
            action = "direct"
            confidence = 0.6
            reasons.append("no_strong_memory_or_risk_signal")

        return PlannerDecision(
            action=action,
            need_memory=need_memory,
            need_reflection=need_reflection,
            need_file_inspection=need_file_inspection,
            ask_clarification=ask_clarification,
            confidence=confidence,
            reasons=reasons,
            retrieved_lesson_count=len(retrieved_lessons),
            top_memory_score=float(top_score),
        )

    @staticmethod
    def to_dict(decision: PlannerDecision) -> dict[str, Any]:
        return asdict(decision)
