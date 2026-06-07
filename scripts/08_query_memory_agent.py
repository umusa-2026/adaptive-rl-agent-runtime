#!/usr/bin/env python3
"""
08_query_memory_agent.py

Query MemoryAgent over learned lessons.
Run:
    python3 scripts/08_query_memory_agent.py --query "MCP settings are lost when saving LLM settings"
"""
from __future__ import annotations

import argparse
from adaptive_runtime.agents.memory import MemoryAgent

def main() -> None:
    parser = argparse.ArgumentParser(description="Query MemoryAgent over learned lessons.")
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--lessons", default="data/learning/lessons.jsonl")
    parser.add_argument("--sqlite", default=None)
    args = parser.parse_args()
    agent = MemoryAgent.from_sqlite(args.sqlite) if args.sqlite else MemoryAgent.from_jsonl(args.lessons)
    results = agent.retrieve(args.query, top_k=args.top_k)
    print("\n=== Query ===")
    print(args.query)
    print("\n=== Retrieved Lessons ===")
    for i, r in enumerate(results, start=1):
        print("\n" + "-" * 80)
        print(f"Rank #{i} | score={r['score']} | domain={r['domain']} | task={r['task_id']}")
        print(f"Issue: {r.get('issue_number')}")
        print(f"Lesson: {r['lesson']}")
        ev = r.get("evidence", {})
        print(f"Evidence URL: {ev.get('url')}")
        print(f"Changed files: {(ev.get('changed_files') or [])[:8]}")
        print(f"Reward signals: {ev.get('reward_signals')}")

if __name__ == "__main__":
    main()
