#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.agents.planner import PlannerAgent
from adaptive_runtime.agents.reflection import ReflectionAgent
from adaptive_runtime.agents.evaluator import EvaluatorAgent
from adaptive_runtime.storage.trajectory_logger import TrajectoryLogger

def main() -> None:
    parser = argparse.ArgumentParser(description="Run Memory + Planner + Reflection + Evaluator + Logger.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--user-acceptance", choices=["accepted", "rejected", "unknown"], default="unknown")
    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--cost-units", type=float, default=1.0)
    parser.add_argument("--log-path", default="data/runtime/trajectories.jsonl")
    parser.add_argument("--data-source", default="synthetic", choices=["synthetic", "github_proxy", "human_feedback", "benchmark_eval"])
    parser.add_argument("--label-confidence", type=float, default=0.5)
    args = parser.parse_args()

    start = time.time()

    memory = MemoryAgent.from_sqlite(args.sqlite)
    lessons = memory.retrieve(args.query, top_k=args.top_k)

    planner = PlannerAgent()
    decision = planner.decide(args.query, lessons)
    decision_dict = PlannerAgent.to_dict(decision)

    reflection = ReflectionAgent()
    report = reflection.reflect(args.query, args.draft, decision_dict, lessons)
    report_dict = ReflectionAgent.to_dict(report)

    latency_sec = time.time() - start

    evaluator = EvaluatorAgent()
    eval_result = evaluator.evaluate(
        reflection_report=report_dict,
        user_acceptance=args.user_acceptance,
        turns=args.turns,
        latency_sec=latency_sec,
        cost_units=args.cost_units,
    )
    eval_dict = EvaluatorAgent.to_dict(eval_result)

    record = {
        "query": args.query,
        "draft_answer": args.draft,
        "retrieved_lessons": lessons,
        "planner_decision": decision_dict,
        "reflection_report": report_dict,
        "evaluation": eval_dict,
        "runtime_metrics": {
            "latency_sec": round(latency_sec, 4),
            "turns": args.turns,
            "cost_units": args.cost_units,
        },
        "data_source": args.data_source,
        "label_confidence": args.label_confidence,
    }

    logger = TrajectoryLogger(args.log_path)
    trajectory_id = logger.log(record)

    print("\n=== Runtime Evaluation ===")
    print(json.dumps(eval_dict, indent=2, ensure_ascii=False))
    print("\n=== Logged Trajectory ===")
    print(f"trajectory_id: {trajectory_id}")
    print(f"path: {args.log_path}")

if __name__ == "__main__":
    main()
