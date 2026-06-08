#!/usr/bin/env python3
import argparse, json
from pathlib import Path
from adaptive_runtime.agents.policy import ContextualBanditPolicy

def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

p = argparse.ArgumentParser()
p.add_argument("--input", default="data/runtime/trajectories.jsonl")
p.add_argument("--output", default="data/policy/bandit_policy.json")
p.add_argument("--epsilon", type=float, default=0.1)
args = p.parse_args()

policy = ContextualBanditPolicy(epsilon=args.epsilon)
rows = read_jsonl(args.input)
for r in rows:
    policy.update_from_record(r)
policy.save(args.output)
print(f"[DONE] trained from {len(rows)} trajectories")
print(f"[WRITE] {args.output}")
for ctx, arms in policy.table.items():
    best = max(arms, key=lambda a: arms[a].mean_reward)
    print(f"{ctx} -> {best}, mean_reward={arms[best].mean_reward:.4f}, count={arms[best].count}")
