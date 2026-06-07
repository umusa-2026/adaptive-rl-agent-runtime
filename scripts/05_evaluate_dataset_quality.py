#!/usr/bin/env python3
"""
05_evaluate_dataset_quality.py

Goal:
    Evaluate dataset quality before it is used by the runtime.

Role in pipeline:
    A self-improving runtime can only learn from useful trajectories.
    This script reports whether trajectories contain the minimum chain:
        problem -> solution -> feedback -> lesson/reward

Run:
    python scripts/05_evaluate_dataset_quality.py

Inputs:
    data/learning/trajectories.jsonl
    data/learning/lessons.jsonl

Outputs:
    data/reports/dataset_quality_report.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RuntimeError(f"Missing input: {path}")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def has_problem(row: dict[str, Any]) -> bool:
    return bool((row.get("problem") or "").strip())


def has_solution(row: dict[str, Any]) -> bool:
    sol = row.get("solution", {})
    return bool((sol.get("text") or "").strip())


def has_feedback(row: dict[str, Any]) -> bool:
    return bool(row.get("feedback"))


def has_linked_pr(row: dict[str, Any]) -> bool:
    return bool(row.get("context", {}).get("linked_prs"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trajectory dataset quality.")
    parser.add_argument("--trajectories", default="data/learning/trajectories.jsonl")
    parser.add_argument("--lessons", default="data/learning/lessons.jsonl")
    parser.add_argument("--output", default="data/reports/dataset_quality_report.md")
    args = parser.parse_args()

    trajectories = read_jsonl(Path(args.trajectories))
    lessons = read_jsonl(Path(args.lessons)) if Path(args.lessons).exists() else []

    total = len(trajectories)
    counts = {
        "has_problem": sum(has_problem(r) for r in trajectories),
        "has_solution": sum(has_solution(r) for r in trajectories),
        "has_feedback": sum(has_feedback(r) for r in trajectories),
        "has_linked_pr": sum(has_linked_pr(r) for r in trajectories),
        "has_reward": sum("reward_signals" in r for r in trajectories),
        "has_lesson": len(lessons),
    }

    flag_counter = Counter()
    task_type_counter = Counter()
    for r in trajectories:
        flag_counter.update(r.get("quality_flags", []))
        task_type_counter.update([r.get("task_type", "unknown")])

    def pct(n: int) -> str:
        return "0.0%" if total == 0 else f"{100.0 * n / total:.1f}%"

    report = []
    report.append("# Dataset Quality Report\n")
    report.append("## Summary\n")
    report.append(f"- Total trajectories: {total}\n")
    for k, v in counts.items():
        denom = total if k != "has_lesson" else max(total, 1)
        report.append(f"- {k}: {v} / {denom} ({pct(v)})\n")

    report.append("\n## Task Type Distribution\n")
    for k, v in task_type_counter.most_common():
        report.append(f"- {k}: {v}\n")

    report.append("\n## Quality Flags\n")
    if flag_counter:
        for k, v in flag_counter.most_common():
            report.append(f"- {k}: {v}\n")
    else:
        report.append("- No quality flags found.\n")

    report.append("\n## Recommended Filters\n")
    report.append("- Strong trajectory: has_problem + has_solution + has_linked_pr\n")
    report.append("- High-value trajectory: strong trajectory + has_feedback\n")
    report.append("- Quarantine: missing_problem or missing_solution\n")

    report.append("\n## Interpretation\n")
    report.append(
        "Use this report to decide whether the dataset is ready for Memory Agent "
        "and Bandit/RL runtime experiments. Do not train/retrieve from low-confidence "
        "trajectories without preserving their raw_refs.\n"
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(report), encoding="utf-8")
    print(f"[WRITE] {out_path}")
    print("\n".join(report[:10]))


if __name__ == "__main__":
    main()
