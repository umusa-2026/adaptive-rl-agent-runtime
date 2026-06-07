#!/usr/bin/env python3
"""
15_generate_trajectory_report.py

Purpose:
    Generate a human-readable Markdown report from runtime trajectories.

Why:
    Keep JSONL for machine/RL training.
    Generate Markdown for human review, GitHub documentation, and debugging.

Run:
    PYTHONPATH=. python3 scripts/15_generate_trajectory_report.py

Output:
    data/runtime/reports/trajectory_report.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RuntimeError(f"Missing trajectory log: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def short(text: Any, limit: int = 1000) -> str:
    text = "" if text is None else str(text)
    text = text.replace("\n", "\n")
    return text if len(text) <= limit else text[:limit] + "...[TRUNCATED]"


def md_escape_table(text: Any) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def generate_report(rows: list[dict[str, Any]], output: Path, last: int | None = None) -> None:
    if last:
        rows_for_detail = rows[-last:]
    else:
        rows_for_detail = rows

    rewards = [r.get("evaluation", {}).get("reward", 0.0) for r in rows]
    accepted = [r.get("evaluation", {}).get("accepted") for r in rows]
    actions = Counter(r.get("planner_decision", {}).get("action", "unknown") for r in rows)
    reflection_pass = Counter(str(r.get("reflection_report", {}).get("passed")) for r in rows)

    lines: list[str] = []
    lines.append("# Runtime Trajectory Report\n\n")

    lines.append("## Summary\n\n")
    lines.append(f"- Total trajectories: {len(rows)}\n")
    if rewards:
        lines.append(f"- Average reward: {sum(rewards) / len(rewards):.3f}\n")
        lines.append(f"- Max reward: {max(rewards):.3f}\n")
        lines.append(f"- Min reward: {min(rewards):.3f}\n")
    lines.append(f"- Accepted: {sum(1 for x in accepted if x is True)}\n")
    lines.append(f"- Rejected: {sum(1 for x in accepted if x is False)}\n")

    lines.append("\n## Planner Action Distribution\n\n")
    for action, count in actions.most_common():
        lines.append(f"- {action}: {count}\n")

    lines.append("\n## Reflection Pass Distribution\n\n")
    for value, count in reflection_pass.most_common():
        lines.append(f"- {value}: {count}\n")

    lines.append("\n## Compact Table\n\n")
    lines.append("| # | Reward | Accepted | Action | Reflection | Query |\n")
    lines.append("|---:|---:|---|---|---|---|\n")
    for i, r in enumerate(rows, start=1):
        lines.append(
            f"| {i} | {r.get('evaluation', {}).get('reward')} | "
            f"{r.get('evaluation', {}).get('accepted')} | "
            f"{md_escape_table(r.get('planner_decision', {}).get('action'))} | "
            f"{r.get('reflection_report', {}).get('passed')} | "
            f"{md_escape_table(short(r.get('query'), 120))} |\n"
        )

    lines.append("\n## Detailed Trajectories\n\n")
    start_idx = max(1, len(rows) - len(rows_for_detail) + 1)
    for offset, r in enumerate(rows_for_detail, start=start_idx):
        lines.append(f"### Trajectory {offset}\n\n")
        lines.append(f"- ID: `{r.get('trajectory_id')}`\n")
        lines.append(f"- Logged at: `{r.get('logged_at')}`\n")
        lines.append(f"- Reward: `{r.get('evaluation', {}).get('reward')}`\n")
        lines.append(f"- Accepted: `{r.get('evaluation', {}).get('accepted')}`\n")
        lines.append(f"- Planner action: `{r.get('planner_decision', {}).get('action')}`\n")
        lines.append(f"- Reflection passed: `{r.get('reflection_report', {}).get('passed')}`\n\n")

        lines.append("#### Query\n\n")
        lines.append(f"```text\n{short(r.get('query'), 1200)}\n```\n\n")

        lines.append("#### Draft Answer\n\n")
        lines.append(f"```text\n{short(r.get('draft_answer'), 1600)}\n```\n\n")

        lines.append("#### Top Retrieved Lessons\n\n")
        lessons = r.get("retrieved_lessons", []) or []
        if not lessons:
            lines.append("_No lessons retrieved._\n\n")
        else:
            for j, l in enumerate(lessons[:5], start=1):
                lines.append(
                    f"{j}. score=`{l.get('score')}`, domain=`{l.get('domain')}`, task=`{l.get('task_id')}`\n\n"
                )
                lines.append(f"   {short(l.get('lesson'), 600)}\n\n")

        lines.append("#### Planner Decision\n\n")
        lines.append(f"```json\n{json.dumps(r.get('planner_decision', {}), indent=2, ensure_ascii=False)}\n```\n\n")

        lines.append("#### Reflection Report\n\n")
        lines.append(f"```json\n{json.dumps(r.get('reflection_report', {}), indent=2, ensure_ascii=False)}\n```\n\n")

        lines.append("#### Evaluation\n\n")
        lines.append(f"```json\n{json.dumps(r.get('evaluation', {}), indent=2, ensure_ascii=False)}\n```\n\n")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(lines), encoding="utf-8")
    print(f"[WRITE] {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Markdown report from runtime trajectories.")
    parser.add_argument("--path", default="data/runtime/trajectories.jsonl")
    parser.add_argument("--output", default="data/runtime/reports/trajectory_report.md")
    parser.add_argument("--last", type=int, default=None, help="Only include detailed view for last N trajectories.")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.path))
    generate_report(rows, Path(args.output), last=args.last)


if __name__ == "__main__":
    main()
