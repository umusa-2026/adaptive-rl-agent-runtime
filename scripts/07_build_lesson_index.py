#!/usr/bin/env python3
"""
07_build_lesson_index.py

Build data/memory/lessons.sqlite from data/learning/lessons.jsonl.
Run:
    python3 scripts/07_build_lesson_index.py
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

def build_index(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise RuntimeError(f"Missing lessons file: {input_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(output_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS lessons")
    cur.execute("""
        CREATE TABLE lessons (
            lesson_id TEXT PRIMARY KEY,
            task_id TEXT,
            repo TEXT,
            issue_number INTEGER,
            domain TEXT,
            trigger TEXT,
            lesson TEXT,
            evidence_json TEXT
        )
    """)
    rows = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        rows.append((
            item.get("lesson_id"),
            item.get("task_id"),
            item.get("repo"),
            item.get("issue_number"),
            item.get("domain"),
            item.get("trigger"),
            item.get("lesson"),
            json.dumps(item.get("evidence", {}), ensure_ascii=False),
        ))
    cur.executemany("""
        INSERT OR REPLACE INTO lessons
        (lesson_id, task_id, repo, issue_number, domain, trigger, lesson, evidence_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_domain ON lessons(domain)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_trigger ON lessons(trigger)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lessons_repo_issue ON lessons(repo, issue_number)")
    conn.commit()
    conn.close()
    print(f"[DONE] Indexed {len(rows)} lessons into {output_path}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Build SQLite lesson index.")
    parser.add_argument("--input", default="data/learning/lessons.jsonl")
    parser.add_argument("--output", default="data/memory/lessons.sqlite")
    args = parser.parse_args()
    build_index(Path(args.input), Path(args.output))

if __name__ == "__main__":
    main()
