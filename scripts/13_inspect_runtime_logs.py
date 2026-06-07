#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect runtime trajectory logs.")
    parser.add_argument("--path", default="data/runtime/trajectories.jsonl")
    parser.add_argument("--last", type=int, default=5)
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise RuntimeError(f"Missing log file: {path}")

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Total trajectories: {len(rows)}")

    for row in rows[-args.last:]:
        print("\n" + "=" * 80)
        print(f"id: {row.get('trajectory_id')}")
        print(f"query: {row.get('query')}")
        print(f"action: {row.get('planner_decision', {}).get('action')}")
        print(f"reflection_passed: {row.get('reflection_report', {}).get('passed')}")
        print(f"reward: {row.get('evaluation', {}).get('reward')}")
        print(f"accepted: {row.get('evaluation', {}).get('accepted')}")
        print(f"missing: {row.get('reflection_report', {}).get('missing_items')}")
        print(f"risks: {row.get('reflection_report', {}).get('risks')}")

if __name__ == "__main__":
    main()
