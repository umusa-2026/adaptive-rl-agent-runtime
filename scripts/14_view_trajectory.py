#!/usr/bin/env python3
"""
14_view_trajectory.py

Purpose:
    Pretty-print runtime trajectories from data/runtime/trajectories.jsonl.

Why:
    JSONL is good for machines and future RL training, but hard for humans to inspect.
    This script gives you a terminal-friendly view.

Run:
    PYTHONPATH=. python3 scripts/14_view_trajectory.py --last 5

Options:
    --path data/runtime/trajectories.jsonl
    --last 5
    --id <trajectory_id>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RuntimeError(f"Missing trajectory log: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def short(text: Any, limit: int = 900) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= limit else text[:limit] + "...[TRUNCATED]"


def print_block(title: str, value: Any = "") -> None:
    print("\n" + "-" * 90)
    print(title)
    print("-" * 90)
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, ensure_ascii=False))
    else:
        print(short(value))


def view(row: dict[str, Any], index: int | None = None) -> None:
    header = f"Trajectory {index}" if index is not None else "Trajectory"
    print("\n" + "=" * 100)
    print(header)
    print("=" * 100)

    print(f"ID: {row.get('trajectory_id')}")
    print(f"Logged at: {row.get('logged_at')}")
    print(f"Reward: {row.get('evaluation', {}).get('reward')}")
    print(f"Accepted: {row.get('evaluation', {}).get('accepted')}")
    print(f"Planner action: {row.get('planner_decision', {}).get('action')}")
    print(f"Reflection passed: {row.get('reflection_report', {}).get('passed')}")

    print_block("Query", row.get("query"))
    print_block("Draft Answer", row.get("draft_answer"))

    lessons = row.get("retrieved_lessons", []) or []
    print_block("Retrieved Lessons Summary", f"{len(lessons)} lessons")
    for i, l in enumerate(lessons[:5], start=1):
        print(f"\n  [{i}] score={l.get('score')} domain={l.get('domain')} task={l.get('task_id')}")
        print(f"      {short(l.get('lesson'), 350)}")

    print_block("Planner Decision", row.get("planner_decision"))
    print_block("Reflection Report", row.get("reflection_report"))
    print_block("Evaluation", row.get("evaluation"))
    print_block("Runtime Metrics", row.get("runtime_metrics"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pretty-print runtime trajectories.")
    parser.add_argument("--path", default="data/runtime/trajectories.jsonl")
    parser.add_argument("--last", type=int, default=5)
    parser.add_argument("--id", default=None, help="Show one trajectory by id.")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.path))

    if args.id:
        matches = [r for r in rows if r.get("trajectory_id") == args.id]
        if not matches:
            raise RuntimeError(f"No trajectory found with id={args.id}")
        view(matches[0])
        return

    selected = rows[-args.last:]
    print(f"Total trajectories: {len(rows)}")
    print(f"Showing last {len(selected)}")
    for i, row in enumerate(selected, start=max(1, len(rows) - len(selected) + 1)):
        view(row, i)


if __name__ == "__main__":
    main()
