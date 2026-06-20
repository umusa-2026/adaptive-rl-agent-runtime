#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Score lesson quality from lesson usage logs.")
    parser.add_argument("--input", default="data/runtime/lesson_usage.jsonl")
    parser.add_argument("--output", default="data/memory/lesson_quality.json")
    parser.add_argument("--applied-weight", type=float, default=1.0)
    parser.add_argument("--retrieved-only-weight", type=float, default=0.2)
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise RuntimeError(f"Missing lesson usage log: {input_path}")

    stats = defaultdict(lambda: {
        "lesson_id": None,
        "domain": None,
        "retrievals": 0,
        "applications": 0,
        "successes": 0,
        "total_reward": 0.0,
        "weighted_reward": 0.0,
        "avg_reward": 0.0,
        "quality_score": 0.0,
    })

    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        row = json.loads(line)
        lesson_id = row.get("lesson_id")
        reward = float(row.get("reward", 0.0))
        applied = bool(row.get("applied"))
        success = bool(row.get("reflection_passed")) and reward > 0

        weight = args.applied_weight if applied else args.retrieved_only_weight

        s = stats[lesson_id]
        s["lesson_id"] = lesson_id
        s["domain"] = s["domain"] or row.get("domain")
        s["retrievals"] += 1
        s["applications"] += int(applied)
        s["successes"] += int(success)
        s["total_reward"] += reward
        s["weighted_reward"] += weight * reward

    output = {}

    for lesson_id, s in stats.items():
        retrievals = max(s["retrievals"], 1)
        applications = max(s["applications"], 1)

        s["avg_reward"] = s["total_reward"] / retrievals
        s["application_rate"] = s["applications"] / retrievals
        s["success_rate"] = s["successes"] / retrievals

        # Simple MVP quality score.
        # Later we can replace this with a learned model.
        s["quality_score"] = (
            0.5 * (s["weighted_reward"] / retrievals)
            + 0.3 * s["success_rate"]
            + 0.2 * s["application_rate"]
        )

        output[lesson_id] = s

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[READ] {input_path}")
    print(f"[WRITE] {output_path}")
    print(f"[COUNT] lessons={len(output)}")

    print("\n=== Top Lessons by Quality ===")
    for lesson_id, s in sorted(output.items(), key=lambda kv: -kv[1]["quality_score"]):
        print()
        print(f"lesson_id: {lesson_id}")
        print(f"  domain: {s['domain']}")
        print(f"  retrievals: {s['retrievals']}")
        print(f"  applications: {s['applications']}")
        print(f"  successes: {s['successes']}")
        print(f"  avg_reward: {s['avg_reward']:.4f}")
        print(f"  quality_score: {s['quality_score']:.4f}")


if __name__ == "__main__":
    main()