#!/usr/bin/env python3
"""
adaptive_runtime/agents/memory.py

Local Memory Agent for Adaptive Coding Runtime.
It retrieves relevant lessons from data/learning/lessons.jsonl or data/memory/lessons.sqlite.
No cloud API, no LLM, no vector DB required.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "into", "when", "then",
    "have", "has", "are", "was", "were", "can", "you", "your", "not", "all",
    "issue", "bug", "fix", "feat", "frontend", "backend", "openhands", "will",
    "should", "would", "could", "there", "their", "about", "using", "use",
}

def tokenize(text: str) -> list[str]:
    if not text:
        return []
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_./-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS]

def infer_query_domain(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["test", "pytest", "ci", "github action", "typecheck", "lint"]):
        return "testing_ci"
    if any(k in t for k in ["docker", "setup", "install", "dependency", "requirements"]):
        return "environment_setup"
    if any(k in t for k in ["doc", "readme", "documentation"]):
        return "documentation"
    if any(k in t for k in ["ui", "frontend", "viewer", "render", "react", "tsx"]):
        return "frontend_ui"
    if any(k in t for k in ["config", "settings", "yaml", "toml", "json", "mcp", "llm"]):
        return "configuration"
    if any(k in t for k in ["agent", "runtime", "tool", "sandbox", "event"]):
        return "agent_runtime"
    if any(k in t for k in ["security", "auth", "authenticated", "permission", "endpoint"]):
        return "security"
    return "general_engineering"

@dataclass
class LessonRecord:
    lesson_id: str
    task_id: str
    repo: str
    issue_number: int | None
    domain: str
    trigger: str
    lesson: str
    evidence: dict[str, Any]

    @property
    def searchable_text(self) -> str:
        changed_files = " ".join(self.evidence.get("changed_files", []) or [])
        labels = " ".join(self.evidence.get("labels", []) or [])
        return f"{self.domain} {self.trigger} {self.lesson} {changed_files} {labels}"

class MemoryAgent:
    def __init__(self, lessons: list[LessonRecord]):
        self.lessons = lessons
        self.doc_tokens = [tokenize(x.searchable_text) for x in lessons]
        self.avgdl = sum(len(toks) for toks in self.doc_tokens) / max(len(self.doc_tokens), 1)
        self.df = self._compute_df(self.doc_tokens)
        self.n_docs = len(self.doc_tokens)

    @staticmethod
    def _compute_df(doc_tokens: list[list[str]]) -> dict[str, int]:
        df: dict[str, int] = {}
        for toks in doc_tokens:
            for tok in set(toks):
                df[tok] = df.get(tok, 0) + 1
        return df

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "MemoryAgent":
        path = Path(path)
        lessons: list[LessonRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            lessons.append(LessonRecord(
                lesson_id=row.get("lesson_id", ""),
                task_id=row.get("task_id", ""),
                repo=row.get("repo", ""),
                issue_number=row.get("issue_number"),
                domain=row.get("domain", "general_engineering"),
                trigger=row.get("trigger", "general"),
                lesson=row.get("lesson", ""),
                evidence=row.get("evidence", {}) or {},
            ))
        return cls(lessons)

    @classmethod
    def from_sqlite(cls, db_path: str | Path) -> "MemoryAgent":
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM lessons").fetchall()
        lessons = []
        for r in rows:
            lessons.append(LessonRecord(
                lesson_id=r["lesson_id"],
                task_id=r["task_id"],
                repo=r["repo"],
                issue_number=r["issue_number"],
                domain=r["domain"],
                trigger=r["trigger"],
                lesson=r["lesson"],
                evidence=json.loads(r["evidence_json"] or "{}"),
            ))
        conn.close()
        return cls(lessons)

    def _bm25_score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        k1 = 1.5
        b = 0.75
        score = 0.0
        doc_len = len(doc_tokens)
        tf: dict[str, int] = {}
        for tok in doc_tokens:
            tf[tok] = tf.get(tok, 0) + 1
        for q in query_tokens:
            if q not in tf:
                continue
            df = self.df.get(q, 0)
            idf = math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
            denom = tf[q] + k1 * (1 - b + b * doc_len / max(self.avgdl, 1e-9))
            score += idf * (tf[q] * (k1 + 1)) / denom
        return score

    def retrieve(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query_tokens = tokenize(query)
        query_domain = infer_query_domain(query)
        scored = []
        for lesson, doc_tokens in zip(self.lessons, self.doc_tokens):
            score = self._bm25_score(query_tokens, doc_tokens)
            if lesson.domain == query_domain:
                score += 2.0
            changed_files = " ".join(lesson.evidence.get("changed_files", []) or []).lower()
            q = query.lower()
            if "frontend" in q and "frontend" in changed_files:
                score += 1.0
            if "enterprise" in q and "enterprise" in changed_files:
                score += 1.0
            if "settings" in q and "settings" in changed_files:
                score += 1.0
            if score > 0:
                scored.append((score, lesson))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{
            "score": round(score, 4),
            "lesson_id": lesson.lesson_id,
            "task_id": lesson.task_id,
            "repo": lesson.repo,
            "issue_number": lesson.issue_number,
            "domain": lesson.domain,
            "trigger": lesson.trigger,
            "lesson": lesson.lesson,
            "evidence": lesson.evidence,
        } for score, lesson in scored[:top_k]]
