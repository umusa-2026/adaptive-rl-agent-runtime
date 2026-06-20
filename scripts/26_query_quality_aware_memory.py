#!/usr/bin/env python3
from __future__ import annotations

import argparse

from adaptive_runtime.agents.memory import MemoryAgent
from adaptive_runtime.rerankers.memory_reranker import MemoryReranker


def print_lesson(rank: int, lesson: dict, mode: str) -> None:
    print()
    print(f"Rank #{rank}")
    print(f"task_id: {lesson.get('task_id')}")
    print(f"domain: {lesson.get('domain')}")

    if mode == "original":
        print(f"retrieval_score: {lesson.get('score')}")
    else:
        print(f"query_domain: {lesson.get('query_domain')}")
        print(f"retrieval_score: {lesson.get('retrieval_score'):.4f}")
        print(f"quality_score: {lesson.get('quality_score'):.4f}")
        print(f"domain_multiplier: {lesson.get('domain_multiplier'):.2f}")
        print(f"final_score: {lesson.get('final_score'):.4f}")

    print(f"lesson: {str(lesson.get('lesson'))[:250]}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query memory and compare original vs quality-aware reranking."
    )

    parser.add_argument("--query", required=True)
    parser.add_argument("--sqlite", default="data/memory/lessons.sqlite")
    parser.add_argument("--quality", default="data/memory/lesson_quality.json")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.2)

    args = parser.parse_args()

    memory = MemoryAgent.from_sqlite(args.sqlite)
    lessons = memory.retrieve(args.query, top_k=args.top_k)

    reranker = MemoryReranker(
        quality_path=args.quality,
        alpha=args.alpha,
    )

    reranked = reranker.rerank(
        query=args.query,
        lessons=lessons,
    )

    print("\n=== Query ===")
    print(args.query)

    print("\n=== Original Ranking ===")
    for i, lesson in enumerate(lessons, start=1):
        print_lesson(i, lesson, mode="original")

    print("\n=== Quality-Aware Ranking ===")
    for i, lesson in enumerate(reranked, start=1):
        print_lesson(i, lesson, mode="reranked")


if __name__ == "__main__":
    main()