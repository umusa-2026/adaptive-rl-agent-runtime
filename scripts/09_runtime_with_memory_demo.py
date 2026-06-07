#!/usr/bin/env python3
"""
09_runtime_with_memory_demo.py

Shows how MemoryAgent will inject context into the future runtime.
Run:
    python3 scripts/09_runtime_with_memory_demo.py --query "Settings are lost when saving LLM settings page"
"""
from __future__ import annotations

import argparse
from adaptive_runtime.agents.memory import MemoryAgent

def build_memory_context(lessons: list[dict]) -> str:
    lines = ["Relevant historical lessons:"]
    for i, item in enumerate(lessons, start=1):
        lines.append(f"\n[{i}] score={item['score']} domain={item['domain']} task={item['task_id']}")
        lines.append(f"Lesson: {item['lesson']}")
        changed = item.get("evidence", {}).get("changed_files") or []
        if changed:
            lines.append(f"Changed files evidence: {', '.join(changed[:6])}")
    return "\n".join(lines)

def main() -> None:
    parser = argparse.ArgumentParser(description="Demo memory-enhanced runtime context.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    agent = MemoryAgent.from_sqlite(args.sqlite)
    lessons = agent.retrieve(args.query, top_k=args.top_k)
    print("\n=== User Task ===")
    print(args.query)
    print("\n=== Memory Context Injected Into Runtime ===")
    print(build_memory_context(lessons))
    print("\n=== Next Runtime Step ===")
    print("Planner should now decide whether to inspect related files, run reflection, or ask clarification.")

if __name__ == "__main__":
    main()
