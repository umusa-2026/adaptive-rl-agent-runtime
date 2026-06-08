#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from collections import Counter
from adaptive_runtime.agents.policy import ContextualBanditPolicy

def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

p = argparse.ArgumentParser()
p.add_argument("--input", default="data/runtime/trajectories.jsonl")
p.add_argument("--policy", default="data/policy/bandit_policy.json")
args = p.parse_args()

rows = read_jsonl(args.input)
policy = ContextualBanditPolicy.load(args.policy)
agree, learned_counts, logged_counts = 0, Counter(), Counter()
for r in rows:
    lessons = r.get("retrieved_lessons", []) or []
    top_score = lessons[0].get("score", 0.0) if lessons else 0.0
    learned = policy.select_action(r.get("query", ""), top_score, len(lessons))["action"]
    logged = r.get("planner_decision", {}).get("action")
    agree += int(learned == logged)
    learned_counts[learned] += 1
    logged_counts[logged] += 1
print(f"Total trajectories: {len(rows)}")
print(f"Policy/planner agreement: {agree}/{len(rows)} = {agree / max(len(rows),1):.2%}")
print("Learned:", dict(learned_counts))
print("Logged:", dict(logged_counts))
