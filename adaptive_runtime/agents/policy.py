#!/usr/bin/env python3
from __future__ import annotations
import json, random, re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ACTIONS = ["direct", "memory_only", "memory_then_reflection", "inspect_files_then_reflect", "ask_clarification"]

@dataclass
class BanditArmStats:
    count: int = 0
    total_reward: float = 0.0
    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.count if self.count else 0.0

class ContextualBanditPolicy:
    def __init__(self, epsilon: float = 0.1):
        self.epsilon = epsilon
        self.table: dict[str, dict[str, BanditArmStats]] = {}

    @staticmethod
    def extract_features(query: str, memory_score: float = 0.0, lesson_count: int = 0) -> dict[str, Any]:
        q = query.lower()
        tokens = re.findall(r"[a-zA-Z0-9_/-]+", q)
        return {
            "query_len_bucket": "short" if len(tokens) < 8 else "medium" if len(tokens) < 20 else "long",
            "memory_bucket": "none" if memory_score <= 0 else "low" if memory_score < 5 else "high" if memory_score < 12 else "very_high",
            "has_lessons": lesson_count > 0,
            "is_bug": any(k in q for k in ["bug", "lost", "reset", "error", "failed", "broken", "not working"]),
            "is_settings": any(k in q for k in ["settings", "mcp", "llm", "config", "payload"]),
            "is_frontend": any(k in q for k in ["frontend", "ui", "render", "viewer", "component", "event", "tool call"]),
            "is_security": any(k in q for k in ["security", "auth", "permission", "endpoint", "access"]),
        }

    @staticmethod
    def context_key(features: dict[str, Any]) -> str:
        return "|".join([
            f"len={features['query_len_bucket']}",
            f"mem={features['memory_bucket']}",
            f"lessons={int(features['has_lessons'])}",
            f"bug={int(features['is_bug'])}",
            f"settings={int(features['is_settings'])}",
            f"frontend={int(features['is_frontend'])}",
            f"security={int(features['is_security'])}",
        ])

    def _ensure_context(self, key: str) -> None:
        if key not in self.table:
            self.table[key] = {a: BanditArmStats() for a in ACTIONS}

    def select_action(self, query: str, memory_score: float = 0.0, lesson_count: int = 0) -> dict[str, Any]:
        features = self.extract_features(query, memory_score, lesson_count)
        key = self.context_key(features)
        self._ensure_context(key)
        if random.random() < self.epsilon:
            action, reason = random.choice(ACTIONS), "epsilon_exploration"
        else:
            action, reason = max(ACTIONS, key=lambda a: self.table[key][a].mean_reward), "best_mean_reward"
        return {
            "action": action,
            "context_key": key,
            "features": features,
            "reason": reason,
            "action_values": {a: {"count": self.table[key][a].count, "mean_reward": round(self.table[key][a].mean_reward, 4)} for a in ACTIONS},
        }

    def update(self, context_key: str, action: str, reward: float) -> None:
        self._ensure_context(context_key)
        arm = self.table[context_key][action]
        arm.count += 1
        arm.total_reward += reward

    def update_from_record(self, record: dict[str, Any]) -> None:
        query = record.get("query", "")
        lessons = record.get("retrieved_lessons", []) or []
        top_score = lessons[0].get("score", 0.0) if lessons else 0.0
        action = record.get("planner_decision", {}).get("action", "direct")
        reward = float(record.get("evaluation", {}).get("reward", 0.0))
        features = self.extract_features(query, top_score, len(lessons))
        self.update(self.context_key(features), action, reward)

    def save(self, path: str | Path) -> None:
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        raw = {"epsilon": self.epsilon, "table": {c: {a: asdict(s) for a, s in arms.items()} for c, arms in self.table.items()}}
        path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "ContextualBanditPolicy":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        obj = cls(raw.get("epsilon", 0.1))
        for c, arms in raw.get("table", {}).items():
            obj.table[c] = {a: BanditArmStats(**s) for a, s in arms.items()}
        return obj
