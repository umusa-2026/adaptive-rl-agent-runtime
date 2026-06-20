#!/usr/bin/env python3
"""
24_review_lesson_usage.py

Review P3.1 lesson usage logs.

Run:
    PYTHONPATH=. python3 scripts/24_review_lesson_usage.py
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Review lesson usage logs.")
    parser.add_argument("--path", default="data/runtime/lesson_usage.jsonl")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise RuntimeError(f"Missing lesson usage log: {path}")

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Total lesson usage events: {len(rows)}")

    stats = defaultdict(lambda: {
        "retrievals": 0,
        "applications": 0,
        "successes": 0,
        "total_reward": 0.0,
        "domain": None,
    })

    for r in rows:
        lid = r.get("lesson_id")
        s = stats[lid]
        s["retrievals"] += 1
        s["applications"] += int(bool(r.get("applied")))
        s["successes"] += int(bool(r.get("reflection_passed")) and float(r.get("reward", 0.0)) > 0)
        s["total_reward"] += float(r.get("reward", 0.0))
        s["domain"] = s["domain"] or r.get("domain")

    print("\n=== Lesson Usage Summary ===")
    for lesson_id, s in sorted(
        stats.items(),
        key=lambda kv: (-(kv[1]["total_reward"] / max(kv[1]["retrievals"], 1)), str(kv[0])),
    ):
        avg_reward = s["total_reward"] / max(s["retrievals"], 1)
        print()
        print(f"lesson_id: {lesson_id}")
        print(f"  domain: {s['domain']}")
        print(f"  retrievals: {s['retrievals']}")
        print(f"  applications: {s['applications']}")
        print(f"  successes: {s['successes']}")
        print(f"  avg_reward: {avg_reward:.4f}")


if __name__ == "__main__":
    main()
