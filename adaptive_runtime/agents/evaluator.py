#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class EvaluationResult:
    accepted: bool
    reward: float
    score_components: dict[str, float]
    labels: dict[str, Any]
    notes: list[str]

class EvaluatorAgent:
    """
    Evaluator Agent.

    Goal:
        Convert runtime outcome into a reward signal.

    MVP reward:
        + reflection passed
        + user accepted / simulated accepted
        - missing items
        - risks
        - too many turns
        - high cost units

    This reward is not perfect. It is a transparent baseline for future bandit/RL.
    """

    def evaluate(
        self,
        reflection_report: dict[str, Any],
        user_acceptance: str = "unknown",
        turns: int = 1,
        latency_sec: float = 0.0,
        cost_units: float = 1.0,
    ) -> EvaluationResult:
        notes = []
        components = {}

        reflection_passed = bool(reflection_report.get("passed"))
        missing_count = len(reflection_report.get("missing_items", []) or [])
        risk_count = len(reflection_report.get("risks", []) or [])

        components["reflection_passed"] = 1.0 if reflection_passed else 0.0
        components["missing_penalty"] = -0.20 * missing_count
        components["risk_penalty"] = -0.10 * risk_count
        components["turn_penalty"] = -0.05 * max(0, turns - 1)
        components["latency_penalty"] = -0.01 * min(latency_sec, 30.0)
        components["cost_penalty"] = -0.05 * cost_units

        if user_acceptance == "accepted":
            components["user_acceptance"] = 1.0
            accepted = True
        elif user_acceptance == "rejected":
            components["user_acceptance"] = -1.0
            accepted = False
        else:
            # In MVP, use reflection as proxy if user signal is unknown.
            components["user_acceptance"] = 0.0
            accepted = reflection_passed

        reward = sum(components.values())

        if not reflection_passed:
            notes.append("Reflection failed; answer should be revised.")
        if missing_count:
            notes.append(f"Missing items: {missing_count}")
        if risk_count:
            notes.append(f"Risks found: {risk_count}")

        return EvaluationResult(
            accepted=accepted,
            reward=round(reward, 4),
            score_components={k: round(v, 4) for k, v in components.items()},
            labels={
                "user_acceptance": user_acceptance,
                "reflection_passed": reflection_passed,
                "turns": turns,
                "latency_sec": latency_sec,
                "cost_units": cost_units,
            },
            notes=notes,
        )

    @staticmethod
    def to_dict(result: EvaluationResult) -> dict[str, Any]:
        return asdict(result)
