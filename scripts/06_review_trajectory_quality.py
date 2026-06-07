#!/usr/bin/env python3

"""
Trajectory Dataset Inspector

Purpose:
    Human review of trajectory quality.

Example:

python scripts/06_review_trajectory_quality.py \
    --repo OpenHands/OpenHands \
    --issues 13969 13971 13972 13975 13991

or

python scripts/06_review_trajectory_quality.py \
    --repo OpenHands/OpenHands \
    --random 5
"""

import argparse
import json
import random
from pathlib import Path


def repo_slug(repo):
    return repo.replace("/", "_")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_section(title, content):
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    if isinstance(content, str):
        print(content[:2000])

    else:
        print(content)


def review_file(path):

    data = load_json(path)

    print("\n\n")
    print("#" * 100)

    print(
        f"Issue #{data['issue_number']}: "
        f"{data['title']}"
    )

    print("#" * 100)

    extracted = data["extracted"]

    print_section(
        "Problem",
        extracted.get("problem", "")
    )

    print_section(
        "Expected Behavior",
        extracted.get("expected_behavior", "")
    )

    print_section(
        "Actual Behavior",
        extracted.get("actual_behavior", "")
    )

    print_section(
        "Reproduction Steps",
        extracted.get("reproduction_steps", "")
    )

    solution = extracted.get(
        "solution_summary",
        {}
    )

    print_section(
        "Selected PR",
        solution.get("selected_pr")
    )

    print_section(
        "Selection Score",
        solution.get("selection_score")
    )

    print_section(
        "Selection Reasons",
        solution.get("selection_reasons")
    )

    print_section(
        "Fix Summary",
        solution.get("fix_summary")
    )

    print_section(
        "Changed Files",
        solution.get("changed_files")
    )

    print_section(
        "Tests",
        solution.get("tests")
    )

    print_section(
        "Candidate Scores",
        solution.get("candidate_scores")
    )

    feedback = extracted.get(
        "feedback",
        []
    )

    print_section(
        f"Feedback Count = {len(feedback)}",
        ""
    )

    for f in feedback[:5]:

        print(
            f"\n[{f.get('source')}] "
            f"{f.get('author')}"
        )

        print(
            f.get("body", "")[:500]
        )

    print_section(
        "Quality Flags",
        data.get("quality_flags", [])
    )

    print("\n")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo",
        required=True
    )

    parser.add_argument(
        "--issues",
        nargs="+",
        type=int
    )

    parser.add_argument(
        "--random",
        type=int
    )

    args = parser.parse_args()

    slug = repo_slug(args.repo)

    traj_dir = (
        Path("data")
        / "processed"
        / "trajectories"
    )

    if args.issues:

        files = []

        for issue_id in args.issues:

            files.append(
                traj_dir /
                f"{slug}_{issue_id}.json"
            )

    else:

        files = list(
            traj_dir.glob(
                f"{slug}_*.json"
            )
        )

        random.shuffle(files)

        n = args.random or 5

        files = files[:n]

    for f in files:

        if not f.exists():

            print(
                f"[WARN] Missing {f}"
            )

            continue

        review_file(f)


if __name__ == "__main__":
    main()