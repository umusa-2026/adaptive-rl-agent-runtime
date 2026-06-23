#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time

from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.agents.reflection import ReflectionAgent
from adaptive_runtime.agents.evaluator import EvaluatorAgent
from adaptive_runtime.storage.trajectory_logger import TrajectoryLogger
from adaptive_runtime.storage.lesson_usage_tracker import LessonUsageTracker
from adaptive_runtime.rerankers.memory_reranker import MemoryReranker


ACTIONS = [
    "direct",
    "memory_only",
    "memory_then_reflection",
    "inspect_files_then_reflect",
    "ask_clarification",
]


def build_manual_decision(action: str, lesson_count: int, top_memory_score: float) -> dict:
    return {
        "action": action,
        "source": "manual_policy_experiment",
        "need_memory": action in [
            "memory_only",
            "memory_then_reflection",
            "inspect_files_then_reflect",
        ],
        "need_reflection": action in [
            "memory_then_reflection",
            "inspect_files_then_reflect",
        ],
        "need_file_inspection": action == "inspect_files_then_reflect",
        "ask_clarification": action == "ask_clarification",
        "confidence": 1.0,
        "reasons": ["manual_policy_experiment"],
        "retrieved_lesson_count": lesson_count,
        "top_memory_score": top_memory_score,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Log explicit policy-action experiment trajectories."
    )

    parser.add_argument("--query", required=True)
    parser.add_argument("--action", required=True, choices=ACTIONS)
    parser.add_argument("--draft", required=True)

    parser.add_argument(
        "--user-acceptance",
        required=True,
        choices=["accepted", "rejected", "unknown"],
    )

    parser.add_argument("--turns", type=int, default=1)
    parser.add_argument("--cost-units", type=float, default=1.0)

    parser.add_argument(
        "--data-source",
        default="synthetic",
        choices=["synthetic", "github_proxy", "human_feedback", "benchmark_eval"],
    )
    parser.add_argument("--label-confidence", type=float, default=0.5)

    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--top-k", type=int, default=5)

    parser.add_argument("--use-quality-reranking", action="store_true")
    parser.add_argument("--quality-path", default="data/memory/lesson_quality.json")
    parser.add_argument("--rerank-alpha", type=float, default=0.2)

    parser.add_argument("--log-path", default="data/runtime/policy_experiments.jsonl")
    parser.add_argument("--lesson-usage-path", default="data/runtime/lesson_usage.jsonl")

    args = parser.parse_args()

    start = time.time()

    memory = MemoryAgent.from_sqlite(args.sqlite)
    lessons = memory.retrieve(args.query, top_k=args.top_k)

    if args.use_quality_reranking:
        reranker = MemoryReranker(
            quality_path=args.quality_path,
            alpha=args.rerank_alpha,
        )
        lessons = reranker.rerank(args.query, lessons)

    top_memory_score = lessons[0].get("final_score", lessons[0].get("score", 0.0)) if lessons else 0.0

    planner_decision = build_manual_decision(
        action=args.action,
        lesson_count=len(lessons),
        top_memory_score=top_memory_score,
    )

    reflection = ReflectionAgent()
    reflection_report = reflection.reflect(
        query=args.query,
        draft_answer=args.draft,
        planner_decision=planner_decision,
        retrieved_lessons=lessons,
    )

    reflection_dict = ReflectionAgent.to_dict(reflection_report)
    latency_sec = time.time() - start

    evaluator = EvaluatorAgent()
    evaluation = evaluator.evaluate(
        reflection_report=reflection_dict,
        user_acceptance=args.user_acceptance,
        turns=args.turns,
        latency_sec=latency_sec,
        cost_units=args.cost_units,
    )

    evaluation_dict = EvaluatorAgent.to_dict(evaluation)

    record = {
        "query": args.query,
        "draft_answer": args.draft,
        "retrieved_lessons": lessons,
        "planner_decision": planner_decision,
        "reflection_report": reflection_dict,
        "evaluation": evaluation_dict,
        "runtime_metrics": {
            "latency_sec": round(latency_sec, 4),
            "turns": args.turns,
            "cost_units": args.cost_units,
        },
        "data_source": args.data_source,
        "label_confidence": args.label_confidence,
        "experiment_type": "manual_policy_action_comparison",
        "quality_reranking_used": args.use_quality_reranking,
    }

    logger = TrajectoryLogger(args.log_path)
    trajectory_id = logger.log(record)

    usage_tracker = LessonUsageTracker(args.lesson_usage_path)
    usage_count = usage_tracker.log_many(
        trajectory_id=trajectory_id,
        query=args.query,
        action=args.action,
        retrieved_lessons=lessons,
        applied_lesson_ids=reflection_dict.get("applied_lessons", []),
        reward=evaluation_dict["reward"],
        reflection_passed=reflection_dict["passed"],
        data_source=args.data_source,
        label_confidence=args.label_confidence,
    )

    print("\n=== Query ===")
    print(args.query)

    print("\n=== Manual Action ===")
    print(args.action)

    print("\n=== Quality Reranking Used ===")
    print(args.use_quality_reranking)

    print("\n=== Planner Decision ===")
    print(json.dumps(planner_decision, indent=2, ensure_ascii=False))

    print("\n=== Reflection Report ===")
    print(json.dumps(reflection_dict, indent=2, ensure_ascii=False))

    print("\n=== Evaluation ===")
    print(json.dumps(evaluation_dict, indent=2, ensure_ascii=False))

    print("\n=== Logged Trajectory ===")
    print(f"trajectory_id: {trajectory_id}")
    print(f"path: {args.log_path}")

    print("\n=== Lesson Usage ===")
    print(f"lesson_usage_events: {usage_count}")
    print(f"path: {args.lesson_usage_path}")


if __name__ == "__main__":
    main()