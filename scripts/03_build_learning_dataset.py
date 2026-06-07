#!/usr/bin/env python3
"""
03_build_learning_dataset.py

Goal:
    Build compact learning-ready records from normalized trajectories.

Role in pipeline:
    The runtime should not train/retrieve directly from messy raw GitHub data.
    It should use compact records containing:
      - problem
      - context
      - solution
      - feedback
      - reward signals

Run:
    python scripts/03_build_learning_dataset.py --repo OpenHands/OpenHands

Inputs:
    data/processed/trajectories/*.json

Outputs:
    data/learning/trajectories.jsonl
    data/learning/reward_events.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def repo_slug(repo: str) -> str:
    return repo.replace("/", "_")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[WRITE] {path} ({len(rows)} rows)")


def infer_task_type(traj: dict[str, Any]) -> str:
    text = " ".join([
        traj.get("title") or "",
        " ".join(traj.get("labels") or []),
        traj.get("extracted", {}).get("problem") or "",
    ]).lower()
    if any(k in text for k in ["bug", "error", "fail", "exception", "traceback"]):
        return "bug_fix"
    if any(k in text for k in ["doc", "readme", "documentation"]):
        return "docs"
    if any(k in text for k in ["feature", "enhancement", "support"]):
        return "feature"
    if any(k in text for k in ["test", "pytest", "ci"]):
        return "test_ci"
    return "general"


def build_reward_signals(traj: dict[str, Any]) -> dict[str, Any]:
    linked_prs = traj.get("linked_prs", [])
    feedback = traj.get("extracted", {}).get("feedback", [])
    flags = traj.get("quality_flags", [])

    merged_pr = any(p.get("merged_at") for p in linked_prs)
    has_solution = bool(traj.get("extracted", {}).get("solution", {}).get("text"))
    has_feedback = bool(feedback)

    # This is not final RL reward. It is weak supervision for evaluation.
    reward = 0.0
    reward += 1.0 if traj.get("state") == "CLOSED" or traj.get("state") == "closed" else 0.0
    reward += 1.0 if merged_pr else 0.0
    reward += 0.5 if has_solution else 0.0
    reward += 0.3 if has_feedback else 0.0
    reward -= 0.2 * len(flags)

    return {
        "closed": traj.get("state"),
        "merged_pr": merged_pr,
        "has_solution": has_solution,
        "has_feedback": has_feedback,
        "quality_flag_count": len(flags),
        "weak_reward": round(reward, 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build learning-ready dataset from trajectories.")
    parser.add_argument("--repo", required=True, help='Repo in "owner/name" format.')
    parser.add_argument("--min-confidence", type=float, default=0.4)
    args = parser.parse_args()

    project_root = Path.cwd()
    slug = repo_slug(args.repo)
    traj_dir = project_root / "data" / "processed" / "trajectories"
    paths = sorted(traj_dir.glob(f"{slug}_*.json"))

    learning_rows = []
    reward_rows = []

    for p in paths:
        traj = load_json(p)
        confidence = traj.get("extracted", {}).get("confidence", 0.0)
        if confidence < args.min_confidence:
            continue

        task_id = f"{traj['repo']}#{traj['issue_number']}"
        reward_signals = build_reward_signals(traj)

        row = {
            "task_id": task_id,
            "repo": traj["repo"],
            "issue_number": traj["issue_number"],
            "url": traj.get("url"),
            "task_type": infer_task_type(traj),
            "problem": traj.get("extracted", {}).get("problem", ""),
            "context": {
                "labels": traj.get("labels", []),
                "expected_behavior": traj.get("extracted", {}).get("expected_behavior", ""),
                "actual_behavior": traj.get("extracted", {}).get("actual_behavior", ""),
                "reproduction_steps": traj.get("extracted", {}).get("reproduction_steps", ""),
                "environment": traj.get("extracted", {}).get("environment", ""),
                "linked_prs": traj.get("linked_prs", []),
            },
            "solution": traj.get("extracted", {}).get("solution", {}),
            "feedback": traj.get("extracted", {}).get("feedback", []),
            "quality_flags": traj.get("quality_flags", []),
            "reward_signals": reward_signals,
        }
        learning_rows.append(row)

        reward_rows.append({
            "task_id": task_id,
            "action": "historical_solution",
            "reward": reward_signals["weak_reward"],
            "signals": reward_signals,
        })

    append_jsonl(project_root / "data" / "learning" / "trajectories.jsonl", learning_rows)
    append_jsonl(project_root / "data" / "learning" / "reward_events.jsonl", reward_rows)
    print("\n[DONE] Built learning dataset.")


if __name__ == "__main__":
    main()
