#!/usr/bin/env python3
"""
06_review_trajectory_quality_v2.py

Trajectory Dataset Inspector v2

Goal:
    Human-review and score processed GitHub issue trajectories.

Why this file matters:
    The earlier dataset quality report only checks whether fields exist.
    For runtime learning, that is not enough.

    Example:
        has_solution=True
    only means:
        the parser found some PR body.
    It does NOT guarantee:
        the selected PR is the correct fix,
        the solution is concise,
        the feedback is useful,
        the trajectory is good for learning.

This inspector helps you check:
    - selected PR correctness
    - candidate PR ranking
    - problem extraction quality
    - reproduction signal
    - feedback usefulness
    - solution summary quality
    - tests / changed files
    - trajectory completeness score

Run from project root:
    python3 scripts/06_review_trajectory_quality_v2.py \
        --repo OpenHands/OpenHands \
        --issues 13969 13971 13972 13975 13991

Random review:
    python3 scripts/06_review_trajectory_quality_v2.py \
        --repo OpenHands/OpenHands \
        --random 5

Show best / worst trajectories:
    python3 scripts/06_review_trajectory_quality_v2.py \
        --repo OpenHands/OpenHands \
        --top 10

    python3 scripts/06_review_trajectory_quality_v2.py \
        --repo OpenHands/OpenHands \
        --worst 10
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def repo_slug(repo: str) -> str:
    return repo.replace("/", "_")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def short(text: str | None, limit: int = 1500) -> str:
    if not text:
        return ""
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit] + "\n...[TRUNCATED]..."


def print_header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def print_sub(title: str) -> None:
    print("\n" + "-" * 80)
    print(title)
    print("-" * 80)


def is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def compute_completeness_score(traj: dict[str, Any]) -> dict[str, Any]:
    """
    Score trajectory quality for runtime learning.

    Total: 100 points

    This is intentionally heuristic, transparent, and easy to modify.
    It is not a scientific metric yet; it is a practical dataset QA tool.
    """
    extracted = traj.get("extracted", {})
    solution_summary = extracted.get("solution_summary", {}) or {}
    feedback = extracted.get("feedback", []) or []
    linked_prs = traj.get("linked_prs", []) or []
    quality_flags = traj.get("quality_flags", []) or []

    score_parts = {}

    # 1. Problem quality, 20 pts.
    problem = extracted.get("problem", "")
    problem_score = 0
    if is_nonempty(problem):
        problem_score += 10
    if len(problem) >= 80:
        problem_score += 5
    # Penalize obvious template-only extraction.
    if "### Bug Description" not in problem and "_No response_" not in problem:
        problem_score += 5
    score_parts["problem"] = min(problem_score, 20)

    # 2. Reproduction / context quality, 15 pts.
    repro_score = 0
    if is_nonempty(extracted.get("reproduction_steps")):
        repro_score += 8
    if is_nonempty(extracted.get("environment")):
        repro_score += 3
    if is_nonempty(extracted.get("actual_behavior")) or is_nonempty(extracted.get("expected_behavior")):
        repro_score += 2
    if is_nonempty(extracted.get("logs")):
        repro_score += 2
    score_parts["reproduction_context"] = min(repro_score, 15)

    # 3. PR link / selected PR quality, 20 pts.
    pr_score = 0
    selected_pr = solution_summary.get("selected_pr")
    selected_score = float(solution_summary.get("selection_score") or 0.0)
    if linked_prs:
        pr_score += 5
    if selected_pr:
        pr_score += 5
    if solution_summary.get("merged_at"):
        pr_score += 4
    if selected_score >= 8:
        pr_score += 4
    elif selected_score >= 5:
        pr_score += 2
    if "explicit_closing_reference" in (solution_summary.get("selection_reasons") or []):
        pr_score += 2
    score_parts["pr_selection"] = min(pr_score, 20)

    # 4. Solution summary quality, 20 pts.
    sol_score = 0
    fix_summary = solution_summary.get("fix_summary", "")
    changed_files = solution_summary.get("changed_files", []) or []
    tests = solution_summary.get("tests", []) or []
    if is_nonempty(fix_summary):
        sol_score += 8
    if len(str(fix_summary)) <= 1200:
        sol_score += 3
    if changed_files:
        sol_score += 4
    if tests:
        sol_score += 5
    score_parts["solution_summary"] = min(sol_score, 20)

    # 5. Feedback / review quality, 15 pts.
    feedback_score = 0
    if feedback:
        feedback_score += 6
    sources = {f.get("source") for f in feedback if isinstance(f, dict)}
    if "pr_review" in sources:
        feedback_score += 4
    if "pr_comment" in sources:
        feedback_score += 3
    if "issue_comment" in sources:
        feedback_score += 2
    score_parts["feedback"] = min(feedback_score, 15)

    # 6. Cleanliness, 10 pts.
    clean_score = 10
    severe_flags = {
        "missing_selected_solution_pr",
        "missing_solution_summary",
        "low_solution_pr_selection_confidence",
    }
    clean_score -= 3 * sum(1 for f in quality_flags if f in severe_flags)
    clean_score -= 1 * sum(1 for f in quality_flags if f not in severe_flags)
    score_parts["cleanliness"] = max(0, min(clean_score, 10))

    total = sum(score_parts.values())

    if total >= 80:
        grade = "A"
        decision = "USE_FOR_RUNTIME_LEARNING"
    elif total >= 65:
        grade = "B"
        decision = "USE_WITH_CAUTION"
    elif total >= 50:
        grade = "C"
        decision = "REVIEW_MANUALLY"
    else:
        grade = "D"
        decision = "QUARANTINE"

    return {
        "total": total,
        "grade": grade,
        "decision": decision,
        "parts": score_parts,
    }


def review_one(path: Path, verbose: bool = True) -> dict[str, Any]:
    traj = load_json(path)
    extracted = traj.get("extracted", {})
    solution_summary = extracted.get("solution_summary", {}) or {}
    feedback = extracted.get("feedback", []) or []
    score = compute_completeness_score(traj)

    if not verbose:
        return {
            "path": str(path),
            "issue_number": traj.get("issue_number"),
            "title": traj.get("title"),
            "score": score["total"],
            "grade": score["grade"],
            "decision": score["decision"],
            "selected_pr": solution_summary.get("selected_pr"),
            "selection_score": solution_summary.get("selection_score"),
            "quality_flags": traj.get("quality_flags", []),
        }

    print_header(f"Issue #{traj.get('issue_number')}: {traj.get('title')}")
    print(f"URL: {traj.get('url')}")
    print(f"State: {traj.get('state')}")
    print(f"Labels: {traj.get('labels')}")
    print(f"Quality flags: {traj.get('quality_flags', [])}")

    print_sub("Completeness Score")
    print(f"Total: {score['total']} / 100")
    print(f"Grade: {score['grade']}")
    print(f"Decision: {score['decision']}")
    print("Parts:")
    for k, v in score["parts"].items():
        print(f"  - {k}: {v}")

    print_sub("Problem")
    print(short(extracted.get("problem", ""), 1800))

    print_sub("Expected Behavior")
    print(short(extracted.get("expected_behavior", ""), 800) or "[EMPTY]")

    print_sub("Actual Behavior")
    print(short(extracted.get("actual_behavior", ""), 800) or "[EMPTY]")

    print_sub("Reproduction Steps")
    print(short(extracted.get("reproduction_steps", ""), 1200) or "[EMPTY]")

    print_sub("Selected PR")
    print(f"selected_pr: {solution_summary.get('selected_pr')}")
    print(f"title: {solution_summary.get('title')}")
    print(f"merged_at: {solution_summary.get('merged_at')}")
    print(f"selection_score: {solution_summary.get('selection_score')}")
    print(f"selection_reasons: {solution_summary.get('selection_reasons')}")

    print_sub("Candidate PR Scores")
    candidates = solution_summary.get("candidate_scores", []) or []
    if not candidates:
        print("[EMPTY]")
    else:
        for c in candidates[:10]:
            print(
                f"PR #{c.get('number')}: score={c.get('score')} "
                f"state={c.get('state')} merged_at={c.get('merged_at')}"
            )
            print(f"  title: {c.get('title')}")
            print(f"  reasons: {c.get('reasons')}")

    print_sub("Fix Summary")
    print(short(solution_summary.get("fix_summary", ""), 1600) or "[EMPTY]")

    print_sub("Changed Files")
    changed_files = solution_summary.get("changed_files", []) or []
    if not changed_files:
        print("[EMPTY]")
    else:
        for f in changed_files[:30]:
            print(f"  - {f}")

    print_sub("Tests")
    tests = solution_summary.get("tests", []) or []
    if not tests:
        print("[EMPTY]")
    else:
        for t in tests[:20]:
            print(f"  - {t}")

    print_sub(f"Feedback Count = {len(feedback)}")
    if not feedback:
        print("[EMPTY]")
    else:
        for i, f in enumerate(feedback[:8], start=1):
            print(f"\n[{i}] source={f.get('source')} author={f.get('author')} state={f.get('state')}")
            print(short(f.get("body", ""), 700) or "[NO BODY]")

    return {
        "path": str(path),
        "issue_number": traj.get("issue_number"),
        "title": traj.get("title"),
        "score": score["total"],
        "grade": score["grade"],
        "decision": score["decision"],
        "selected_pr": solution_summary.get("selected_pr"),
        "selection_score": solution_summary.get("selection_score"),
        "quality_flags": traj.get("quality_flags", []),
    }


def get_files(repo: str, issues: list[int] | None, random_n: int | None, top: int | None, worst: int | None) -> list[Path]:
    slug = repo_slug(repo)
    traj_dir = Path("data") / "processed" / "trajectories"

    if issues:
        return [traj_dir / f"{slug}_{i}.json" for i in issues]

    all_files = sorted(traj_dir.glob(f"{slug}_*.json"))
    if not all_files:
        raise RuntimeError(f"No trajectory files found under {traj_dir} for repo {repo}")

    if random_n:
        files = all_files[:]
        random.shuffle(files)
        return files[:random_n]

    if top or worst:
        summaries = []
        for p in all_files:
            summaries.append(review_one(p, verbose=False))
        summaries.sort(key=lambda x: x["score"], reverse=bool(top))
        selected = summaries[: (top or worst)]
        return [Path(x["path"]) for x in selected]

    return all_files[:5]


def write_summary_report(rows: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Trajectory Review Summary\n\n")
    lines.append("| Issue | Score | Grade | Decision | Selected PR | Flags | Title |\n")
    lines.append("|---:|---:|---|---|---:|---|---|\n")
    for r in rows:
        flags = ", ".join(r.get("quality_flags") or [])
        lines.append(
            f"| {r['issue_number']} | {r['score']} | {r['grade']} | "
            f"{r['decision']} | {r.get('selected_pr')} | {flags} | {str(r.get('title', '')).replace('|', '/')} |\n"
        )
    output.write_text("".join(lines), encoding="utf-8")
    print(f"\n[WRITE] {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Review and score processed issue trajectories.")
    parser.add_argument("--repo", required=True, help='Repo in "owner/name" format.')
    parser.add_argument("--issues", nargs="+", type=int, help="Specific issue numbers to inspect.")
    parser.add_argument("--random", type=int, help="Randomly inspect N trajectories.")
    parser.add_argument("--top", type=int, help="Inspect top N highest-scoring trajectories.")
    parser.add_argument("--worst", type=int, help="Inspect worst N lowest-scoring trajectories.")
    parser.add_argument("--summary-only", action="store_true", help="Only print compact summary table.")
    parser.add_argument("--write-report", default="data/reports/trajectory_review_summary.md")
    args = parser.parse_args()

    files = get_files(args.repo, args.issues, args.random, args.top, args.worst)
    rows = []

    for f in files:
        if not f.exists():
            print(f"[WARN] Missing {f}")
            continue
        rows.append(review_one(f, verbose=not args.summary_only))

    print_header("Compact Summary")
    for r in rows:
        print(
            f"Issue #{r['issue_number']} | score={r['score']} | grade={r['grade']} | "
            f"decision={r['decision']} | selected_pr={r.get('selected_pr')} | title={r.get('title')}"
        )

    write_summary_report(rows, Path(args.write_report))


if __name__ == "__main__":
    main()
