# GitHub Issue Trajectory Data Pipeline

This pipeline converts messy GitHub issues into learning-ready trajectories for an adaptive coding-agent runtime.

## Pipeline workflow

```text
GitHub repo
   |
   | 01_collect_github_trajectory_dataset.py
   v
data/raw/
   ├── issue_lists/
   ├── issues/
   ├── timelines/
   ├── prs/
   └── manifests/
   |
   | 02_parse_issue_trajectory.py
   v
data/processed/trajectories/
   |
   | 03_build_learning_dataset.py
   v
data/learning/
   ├── trajectories.jsonl
   └── reward_events.jsonl
   |
   | 04_generate_lessons.py
   v
data/learning/lessons.jsonl
   |
   | 05_evaluate_dataset_quality.py
   v
data/reports/dataset_quality_report.md
```

## File roles

| Script | Goal | Input | Output |
|---|---|---|---|
| `01_collect_github_trajectory_dataset.py` | Collect raw GitHub issue, timeline, PR data without summarizing | GitHub CLI / GitHub repo | `data/raw/` |
| `02_parse_issue_trajectory.py` | Normalize raw data into canonical trajectories | `data/raw/` | `data/processed/trajectories/` |
| `03_build_learning_dataset.py` | Build compact learning records and weak reward events | `data/processed/trajectories/` | `data/learning/trajectories.jsonl`, `reward_events.jsonl` |
| `04_generate_lessons.py` | Generate deterministic no-LLM lessons for Memory Agent | `data/learning/trajectories.jsonl` | `data/learning/lessons.jsonl` |
| `05_evaluate_dataset_quality.py` | Report dataset quality and missing trajectory components | `data/learning/*.jsonl` | `data/reports/dataset_quality_report.md` |

## Run order

From project root:

```bash
python scripts/01_collect_github_trajectory_dataset.py --repo OpenHands/OpenHands --limit 50
python scripts/02_parse_issue_trajectory.py --repo OpenHands/OpenHands
python scripts/03_build_learning_dataset.py --repo OpenHands/OpenHands
python scripts/04_generate_lessons.py
python scripts/05_evaluate_dataset_quality.py
```

## Why this design

The pipeline is raw-first and lossless. It preserves raw data before extraction because issue formats are flexible and important signals may appear in different places:
- issue body
- comments
- timeline events
- linked PRs
- PR reviews
- changed files
- commit messages

The runtime should learn from the normalized layer, but every processed trajectory keeps `raw_refs` so future parsers can reprocess the raw artifacts.
