#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.agents.planner import PlannerAgent
from adaptive_runtime.agents.reflection import ReflectionAgent

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Reflection Agent on a draft answer.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    memory = MemoryAgent.from_sqlite(args.sqlite)
    lessons = memory.retrieve(args.query, top_k=args.top_k)

    planner = PlannerAgent()
    decision = planner.decide(args.query, lessons)
    decision_dict = PlannerAgent.to_dict(decision)

    reflection = ReflectionAgent()
    report = reflection.reflect(args.query, args.draft, decision_dict, lessons)
    report_dict = ReflectionAgent.to_dict(report)

    print("\n=== Query ===")
    print(args.query)
    print("\n=== Draft Answer ===")
    print(args.draft)
    print("\n=== Planner Decision ===")
    print(json.dumps(decision_dict, indent=2, ensure_ascii=False))
    print("\n=== Reflection Report ===")
    print(json.dumps(report_dict, indent=2, ensure_ascii=False))
    print("\n=== Next Action ===")
    print("Draft passes reflection. Runtime can proceed." if report.passed else "Draft failed reflection. Runtime should revise using recommendations.")

if __name__ == "__main__":
    main()
