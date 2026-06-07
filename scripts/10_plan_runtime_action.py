#!/usr/bin/env python3
"""
10_plan_runtime_action.py

Goal:
    Demonstrate MemoryAgent + PlannerAgent.

Flow:
    query
      ↓
    MemoryAgent.retrieve(query)
      ↓
    PlannerAgent.decide(query, lessons)
      ↓
    runtime action

Run:
    PYTHONPATH=. python3 scripts/10_plan_runtime_action.py \
      --query "MCP server settings are lost when saving LLM settings"

    PYTHONPATH=. python3 scripts/10_plan_runtime_action.py \
      --query "Render ACP tool calls in the conversation viewer"
"""

from __future__ import annotations

import argparse
import json

from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.agents.planner import PlannerAgent


def print_lessons(lessons: list[dict], max_len: int = 500) -> None:
    print("\n=== Retrieved Memory Lessons ===")
    if not lessons:
        print("[EMPTY]")
        return

    for i, item in enumerate(lessons, start=1):
        print("\n" + "-" * 80)
        print(f"Rank #{i} | score={item['score']} | domain={item['domain']} | task={item['task_id']}")
        lesson = item["lesson"]
        if len(lesson) > max_len:
            lesson = lesson[:max_len] + "...[TRUNCATED]"
        print(lesson)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan runtime action with Memory + Planner agents.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON only.")
    args = parser.parse_args()

    memory = MemoryAgent.from_sqlite(args.sqlite)
    lessons = memory.retrieve(args.query, top_k=args.top_k)

    planner = PlannerAgent()
    decision = planner.decide(args.query, lessons)
    decision_dict = PlannerAgent.to_dict(decision)

    if args.json:
        print(json.dumps({
            "query": args.query,
            "decision": decision_dict,
            "top_lessons": lessons,
        }, indent=2, ensure_ascii=False))
        return

    print("\n=== Query ===")
    print(args.query)

    print_lessons(lessons)

    print("\n=== Planner Decision ===")
    print(json.dumps(decision_dict, indent=2, ensure_ascii=False))

    print("\n=== Interpretation ===")
    action = decision.action
    if action == "inspect_files_then_reflect":
        print("Runtime should retrieve memory, inspect files suggested by evidence, then run Reflection Agent before final answer.")
    elif action == "memory_then_reflection":
        print("Runtime should inject memory lessons, draft answer, then run Reflection Agent to check for missed constraints.")
    elif action == "memory_only":
        print("Runtime should inject memory lessons into the answer path; reflection is optional.")
    elif action == "ask_clarification":
        print("Runtime should ask the user for missing details before proceeding.")
    elif action == "reflection_only":
        print("Runtime should answer but run Reflection Agent because the task looks risky/debug-oriented.")
    else:
        print("Runtime can use a simple direct path.")


if __name__ == "__main__":
    main()
