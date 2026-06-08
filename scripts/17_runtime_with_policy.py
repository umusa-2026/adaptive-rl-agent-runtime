#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.agents.planner import PlannerAgent
from adaptive_runtime.agents.policy import ContextualBanditPolicy

p = argparse.ArgumentParser()
p.add_argument("--query", required=True)
p.add_argument("--sqlite", default="data/memory/lessons.sqlite")
p.add_argument("--policy", default="data/policy/bandit_policy.json")
p.add_argument("--top-k", type=int, default=5)
args = p.parse_args()

memory = MemoryAgent.from_sqlite(args.sqlite)
lessons = memory.retrieve(args.query, top_k=args.top_k)
top_score = lessons[0]["score"] if lessons else 0.0
rule = PlannerAgent().decide(args.query, lessons)
policy = ContextualBanditPolicy.load(args.policy) if Path(args.policy).exists() else ContextualBanditPolicy(epsilon=0.0)
learned = policy.select_action(args.query, top_score, len(lessons))

print("\n=== Query ===")
print(args.query)
print("\n=== Rule-Based Planner ===")
print(json.dumps(PlannerAgent.to_dict(rule), indent=2, ensure_ascii=False))
print("\n=== Learned Bandit Policy ===")
print(json.dumps(learned, indent=2, ensure_ascii=False))
