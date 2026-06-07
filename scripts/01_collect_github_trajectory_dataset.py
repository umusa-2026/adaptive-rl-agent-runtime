#!/usr/bin/env python3
"""
01_collect_github_trajectory_dataset.py

Goal:
    Collect raw GitHub issue trajectory artifacts without losing information.

Role in pipeline:
    This is the raw-data collector. It does NOT summarize or interpret.
    It preserves:
      - issue list
      - issue body + comments
      - issue timeline
      - linked PR details when discoverable

Why raw-first:
    GitHub issue formats are inconsistent. The "problem", "feedback",
    "solution", and "lesson" may appear in the issue body, comments,
    timeline cross-references, linked PR body, PR reviews, or commits.
    Therefore, raw data must be preserved before any parsing.

Requirements:
    brew install gh jq
    gh auth login

Run from project root:
    python scripts/01_collect_github_trajectory_dataset.py \
        --repo OpenHands/OpenHands \
        --limit 50

Outputs:
    data/raw/issue_lists/<repo>_closed_issues.json
    data/raw/issues/<repo>_<issue>.json
    data/raw/timelines/<repo>_<issue>.json
    data/raw/prs/<repo>_<pr>.json
    data/raw/manifests/<repo>_collection_manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(cmd: list[str]) -> str:
    print(f"\n[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("[ERROR] Command failed.", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return result.stdout


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[WRITE] {path}")


def load_json_if_exists(path: Path) -> Any | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def repo_slug(repo: str) -> str:
    return repo.replace("/", "_")


def ensure_project_root() -> Path:
    cwd = Path.cwd()
    if not (cwd / "scripts").exists():
        raise RuntimeError(
            "Run from project root, for example:\n"
            "  cd adaptive-coding-runtime\n"
            "  python scripts/01_collect_github_trajectory_dataset.py --repo OpenHands/OpenHands --limit 50"
        )
    return cwd


def collect_closed_issue_list(repo: str, limit: int, project_root: Path, force: bool) -> list[dict[str, Any]]:
    out_path = project_root / "data" / "raw" / "issue_lists" / f"{repo_slug(repo)}_closed_issues.json"
    cached = None if force else load_json_if_exists(out_path)
    if cached is not None:
        print(f"[CACHE] {out_path}")
        return cached

    output = run_command([
        "gh", "issue", "list",
        "--repo", repo,
        "--state", "closed",
        "--limit", str(limit),
        "--json", "number,title,state,labels,author,createdAt,closedAt,url",
    ])
    issues = json.loads(output)
    write_json(out_path, issues)
    return issues


def collect_issue_detail(repo: str, issue_number: int, project_root: Path, force: bool) -> dict[str, Any]:
    out_path = project_root / "data" / "raw" / "issues" / f"{repo_slug(repo)}_{issue_number}.json"
    cached = None if force else load_json_if_exists(out_path)
    if cached is not None:
        print(f"[CACHE] {out_path}")
        return cached

    output = run_command([
        "gh", "issue", "view", str(issue_number),
        "--repo", repo,
        "--comments",
        "--json", "number,title,body,state,labels,author,createdAt,closedAt,url,comments",
    ])
    issue = json.loads(output)
    write_json(out_path, issue)
    return issue


def collect_issue_timeline(repo: str, issue_number: int, project_root: Path, force: bool) -> list[dict[str, Any]]:
    out_path = project_root / "data" / "raw" / "timelines" / f"{repo_slug(repo)}_{issue_number}.json"
    cached = None if force else load_json_if_exists(out_path)
    if cached is not None:
        print(f"[CACHE] {out_path}")
        return cached

    output = run_command(["gh", "api", f"repos/{repo}/issues/{issue_number}/timeline", "--paginate"])
    try:
        timeline = json.loads(output)
    except json.JSONDecodeError:
        # Defensive fallback if gh prints multiple arrays.
        timeline = []
        for match in re.finditer(r"\[[\s\S]*?\]", output):
            try:
                timeline.extend(json.loads(match.group(0)))
            except json.JSONDecodeError:
                pass
    write_json(out_path, timeline)
    return timeline


def extract_pr_numbers_from_text(text: str) -> set[int]:
    """Extract explicit PR numbers from /pull/<number> links."""
    return {int(m.group(1)) for m in re.finditer(r"/pull/(\d+)", text or "")}


def extract_pr_numbers_from_issue(issue: dict[str, Any]) -> set[int]:
    pr_numbers = set()
    pr_numbers.update(extract_pr_numbers_from_text(issue.get("body", "")))
    for c in issue.get("comments", []):
        pr_numbers.update(extract_pr_numbers_from_text(c.get("body", "")))
    return pr_numbers


def extract_pr_numbers_from_timeline(timeline: list[dict[str, Any]]) -> set[int]:
    pr_numbers = set()
    for event in timeline:
        pr_numbers.update(extract_pr_numbers_from_text(json.dumps(event, ensure_ascii=False)))
    return pr_numbers


def collect_pr_detail(repo: str, pr_number: int, project_root: Path, force: bool) -> dict[str, Any] | None:
    out_path = project_root / "data" / "raw" / "prs" / f"{repo_slug(repo)}_{pr_number}.json"
    cached = None if force else load_json_if_exists(out_path)
    if cached is not None:
        print(f"[CACHE] {out_path}")
        return cached

    # IMPORTANT: `merged` is not a valid gh PR JSON field. Use mergedAt/state/closed.
    fields = (
        "number,title,body,state,closed,closedAt,mergedAt,mergeCommit,"
        "mergeStateStatus,author,createdAt,updatedAt,url,files,commits,"
        "reviews,comments,labels,reviewDecision,changedFiles,additions,deletions"
    )
    try:
        output = run_command(["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", fields])
    except RuntimeError:
        print(f"[WARN] Could not fetch PR #{pr_number}. It may be unavailable or not a PR.")
        return None

    pr = json.loads(output)
    write_json(out_path, pr)
    return pr


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect raw GitHub issue trajectory data.")
    parser.add_argument("--repo", required=True, help='Repo in "owner/name" format.')
    parser.add_argument("--limit", type=int, default=50, help="Number of closed issues to collect.")
    parser.add_argument("--skip-prs", action="store_true", help="Skip linked PR collection.")
    parser.add_argument("--force", action="store_true", help="Re-download existing raw files.")
    args = parser.parse_args()

    project_root = ensure_project_root()
    manifest: dict[str, Any] = {"repo": args.repo, "issues": []}

    issues = collect_closed_issue_list(args.repo, args.limit, project_root, args.force)

    for item in issues:
        issue_number = item["number"]
        print(f"\n=== Issue #{issue_number}: {item.get('title', '')} ===")
        record: dict[str, Any] = {"issue_number": issue_number, "linked_prs": []}

        issue = collect_issue_detail(args.repo, issue_number, project_root, args.force)
        timeline = collect_issue_timeline(args.repo, issue_number, project_root, args.force)

        if not args.skip_prs:
            pr_numbers = set()
            pr_numbers.update(extract_pr_numbers_from_issue(issue))
            pr_numbers.update(extract_pr_numbers_from_timeline(timeline))
            record["linked_prs"] = sorted(pr_numbers)

            if not pr_numbers:
                print(f"[INFO] No explicit linked PRs discovered for issue #{issue_number}.")
            for pr_number in sorted(pr_numbers):
                collect_pr_detail(args.repo, pr_number, project_root, args.force)

        manifest["issues"].append(record)

    manifest_path = project_root / "data" / "raw" / "manifests" / f"{repo_slug(args.repo)}_collection_manifest.json"
    write_json(manifest_path, manifest)
    print("\n[DONE] Raw collection complete.")


if __name__ == "__main__":
    main()
