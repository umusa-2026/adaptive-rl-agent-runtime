#!/usr/bin/env python3
"""
04_generate_lessons_v3.py

Trajectory-derived lesson generator.

v2 problem:
    Lessons were domain-specific but still mostly hard-coded templates.

v3 goal:
    Generate lessons from the actual trajectory:
      - problem
      - solution / fix summary
      - changed files
      - feedback / review comments
      - reward signals

Design:
    No LLM.
    No cloud API.
    Deterministic and reproducible.

Run:
    PYTHONPATH=. python3 scripts/04_generate_lessons.py

Then:
    PYTHONPATH=. python3 scripts/07_build_lesson_index.py
    PYTHONPATH=. python3 scripts/08_query_memory_agent.py \
      --query "MCP server settings are lost when saving LLM settings"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STOP = {
    "the", "and", "for", "with", "from", "this", "that", "issue", "bug", "fix",
    "feat", "openhands", "response", "expected", "actual", "there", "when",
    "then", "they", "them", "your", "have", "has", "into", "using", "user",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise RuntimeError(f"Missing input: {path}")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[WRITE] {path} ({len(rows)} rows)")


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def first_sentence(text: str, limit: int = 260) -> str:
    text = clean(text)
    if not text:
        return ""
    # Keep short bullet-like summaries intact.
    sentence = re.split(r"(?<=[.!?])\s+", text)[0]
    if len(sentence) > limit:
        sentence = sentence[:limit].rstrip() + "..."
    return sentence


def changed_files(row: dict[str, Any]) -> list[str]:
    files: list[str] = []
    for pr in row.get("context", {}).get("linked_prs", []) or []:
        files.extend(pr.get("changed_files") or [])
    sol = row.get("solution", {})
    if isinstance(sol, dict):
        files.extend(sol.get("changed_files") or [])
    seen, out = set(), []
    for f in files:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return out


def get_problem(row: dict[str, Any]) -> str:
    return clean(row.get("problem", ""))


def get_solution_text(row: dict[str, Any]) -> str:
    sol = row.get("solution", {}) or {}
    return clean(sol.get("text", "") if isinstance(sol, dict) else "")


def extract_pr_title(solution_text: str) -> str:
    m = re.search(r"PR #\d+:\s*(.+)", solution_text)
    return clean(m.group(1)) if m else ""


def extract_section_bullets(text: str, names: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    bullets: list[str] = []
    in_section = False
    pattern = "|".join(re.escape(n) for n in names)

    for line in lines:
        s = line.strip()
        lower = s.lower()
        if re.match(rf"^#{{1,6}}\s*({pattern})\b", lower):
            in_section = True
            continue
        if in_section and re.match(r"^#{1,6}\s+", s):
            break
        if in_section and re.match(r"^[-*]\s+", s):
            bullets.append(clean(re.sub(r"^[-*]\s+", "", s)))
    return [b for b in bullets if b][:6]


def extract_fix_summary(row: dict[str, Any]) -> str:
    text = get_solution_text(row)
    if not text:
        return ""

    bullets = extract_section_bullets(text, ("summary", "changes", "why", "description"))
    if bullets:
        return "; ".join(bullets[:4])

    title = extract_pr_title(text)
    if title:
        return title

    return first_sentence(text, 400)


def extract_tests(row: dict[str, Any]) -> list[str]:
    text = get_solution_text(row)
    tests: list[str] = []
    in_testing = False
    for line in text.splitlines():
        s = line.strip()
        lower = s.lower()
        if re.match(r"^#{1,6}\s*(testing|how to test)\b", lower):
            in_testing = True
            continue
        if in_testing and re.match(r"^#{1,6}\s+", s):
            break
        if in_testing and s:
            if any(k in s for k in ["npm run", "pytest", "typecheck", "lint", "build", "test "]):
                tests.append(s)
    for line in text.splitlines():
        s = line.strip()
        if any(k in s for k in ["npm run", "pytest", "typecheck", "lint", "build", "test "]):
            if s not in tests and not s.lower().startswith(("fixes #", "related to #")):
                tests.append(s)
    return tests[:10]


def feedback_signals(row: dict[str, Any]) -> list[str]:
    feedback = row.get("feedback", []) or []
    signals: list[str] = []
    for item in feedback:
        body = clean(item.get("body", ""))
        state = item.get("state")
        source = item.get("source")
        if not body and state:
            body = f"{source} state={state}"
        if not body:
            continue

        # Keep only useful review signals.
        lower = body.lower()
        useful = any(k in lower for k in [
            "risk", "test", "coverage", "missing", "should", "needs", "confirmed",
            "verified", "fix", "regression", "architecture", "good taste",
            "defensive", "security", "merge conflict", "ci",
        ])
        if useful:
            signals.append(first_sentence(body, 260))
    return signals[:5]


def get_text(row: dict[str, Any]) -> str:
    ctx = row.get("context", {}) or {}
    return "\n".join([
        get_problem(row),
        row.get("task_type", ""),
        " ".join(ctx.get("labels", []) or []),
        ctx.get("expected_behavior", ""),
        ctx.get("actual_behavior", ""),
        ctx.get("reproduction_steps", ""),
        get_solution_text(row),
        " ".join(changed_files(row)),
    ]).lower()


def infer_domain(row: dict[str, Any]) -> str:
    text = get_text(row)
    if any(k in text for k in ["mcp", "llm settings", "settings page", "basic", "advanced", "save payload", "tavily", "verification settings", "mcp_config"]):
        return "settings_configuration"
    if any(k in text for k in ["acptoolcallevent", "conversation viewer", "render", "event-message", "generic event", "tool call", "tool_call_id"]):
        return "frontend_event_rendering"
    if any(k in text for k in ["shared conversation", "endpoint", "authenticated", "enumeration", "permission", "security"]):
        return "security_endpoint"
    if any(k in text for k in ["agent", "runtime", "sandbox", "tool", "event stream"]):
        return "agent_runtime"
    if any(k in text for k in ["test", "pytest", "ci", "github action", "typecheck", "lint"]):
        return "testing_ci"
    if any(k in text for k in ["docker", "setup", "install", "dependency", "requirements"]):
        return "environment_setup"
    if any(k in text for k in ["doc", "readme", "documentation"]):
        return "documentation"
    if any(k in text for k in ["ui", "frontend", "viewer", "react", "tsx"]):
        return "frontend_ui"
    return "general_engineering"


def infer_trigger(row: dict[str, Any], domain: str) -> str:
    text = get_text(row)
    if domain == "settings_configuration":
        if "mcp" in text and "llm" in text:
            return "cross_section_settings_persistence"
        if "basic" in text and "advanced" in text:
            return "basic_advanced_settings_view"
        return "settings_save_behavior"
    if domain == "frontend_event_rendering":
        return "new_event_type_rendering"
    if domain == "security_endpoint":
        return "unauthenticated_endpoint_or_enumeration"
    if domain == "agent_runtime":
        return "agent_runtime_lifecycle"
    if domain == "testing_ci":
        return "test_or_ci_failure"
    return row.get("task_type", "general")


def relevant_files_summary(files: list[str]) -> str:
    if not files:
        return ""
    # Focus on non-artifact files first.
    keep = [
        f for f in files
        if not f.startswith(".pr/")
        and not f.endswith((".png", ".gif", ".jpg", ".jpeg"))
        and ".gitattributes" not in f
        and "translation.json" not in f
    ]
    if not keep:
        keep = files
    return ", ".join(keep[:6])


def make_trajectory_derived_lesson(row: dict[str, Any], domain: str, trigger: str) -> str:
    problem = first_sentence(get_problem(row), 280)
    fix = extract_fix_summary(row)
    files = changed_files(row)
    file_summary = relevant_files_summary(files)
    signals = feedback_signals(row)
    tests = extract_tests(row)

    lesson_parts: list[str] = []

    # Domain-specific opening, but filled with trajectory-specific evidence.
    if domain == "settings_configuration":
        lesson_parts.append(
            "When a settings change causes data loss across pages, model settings as ownership boundaries rather than one shared payload."
        )
    elif domain == "frontend_event_rendering":
        lesson_parts.append(
            "When adding a new frontend event type, trace the full rendering pipeline instead of adding an isolated component."
        )
    elif domain == "security_endpoint":
        lesson_parts.append(
            "When an endpoint exposes enumeration or unauthenticated access, remove or restrict the broad route while preserving the minimal legitimate access path."
        )
    elif domain == "agent_runtime":
        lesson_parts.append(
            "For agent-runtime changes, trace lifecycle events, state transitions, tool calls, and error propagation end-to-end."
        )
    elif domain == "testing_ci":
        lesson_parts.append(
            "For test or CI failures, identify the smallest failing path and add focused regression coverage."
        )
    else:
        lesson_parts.append(
            "Use the accepted fix trajectory as evidence before proposing a solution."
        )

    if problem:
        lesson_parts.append(f"Problem pattern: {problem}")

    if fix:
        lesson_parts.append(f"Accepted fix pattern: {fix}")

    if file_summary:
        lesson_parts.append(f"Evidence files: {file_summary}.")

    if tests:
        lesson_parts.append(f"Validation pattern: {'; '.join(tests[:3])}")

    if signals:
        lesson_parts.append(f"Review signal: {signals[0]}")

    return " ".join(lesson_parts)


def make_search_keywords(row: dict[str, Any], domain: str, trigger: str) -> list[str]:
    text = get_text(row)
    words = {domain, trigger}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text):
        t = token.lower()
        if t in STOP:
            continue
        if any(k in t for k in [
            "mcp", "llm", "tavily", "settings", "verification", "acptoolcall",
            "conversation", "viewer", "endpoint", "shared", "auth", "payload",
            "render", "event", "tool", "config",
        ]):
            words.add(t)
    for f in changed_files(row):
        for part in re.split(r"[/_.-]+", f.lower()):
            if len(part) >= 3 and part not in {"src", "test", "tests", "frontend", "backend"}:
                words.add(part)
    return sorted(words)[:50]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate trajectory-derived lessons.")
    parser.add_argument("--input", default="data/learning/trajectories.jsonl")
    parser.add_argument("--output", default="data/learning/lessons.jsonl")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    lessons = []

    for row in rows:
        domain = infer_domain(row)
        trigger = infer_trigger(row, domain)
        lesson_text = make_trajectory_derived_lesson(row, domain, trigger)
        files = changed_files(row)

        lessons.append({
            "lesson_id": row["task_id"],
            "task_id": row["task_id"],
            "repo": row["repo"],
            "issue_number": row["issue_number"],
            "domain": domain,
            "trigger": trigger,
            "lesson": lesson_text,
            "search_keywords": make_search_keywords(row, domain, trigger),
            "evidence": {
                "url": row.get("url"),
                "labels": row.get("context", {}).get("labels", []),
                "changed_files": files[:30],
                "fix_summary": extract_fix_summary(row),
                "feedback_signals": feedback_signals(row),
                "tests": extract_tests(row),
                "has_feedback": bool(row.get("feedback")),
                "reward_signals": row.get("reward_signals", {}),
            },
        })

    write_jsonl(Path(args.output), lessons)
    print("\n[DONE] Generated trajectory-derived lessons.")


if __name__ == "__main__":
    main()
