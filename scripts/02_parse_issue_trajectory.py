#!/usr/bin/env python3
"""
02_parse_issue_trajectory.py

Goal:
    Convert raw GitHub artifacts into normalized issue trajectories.

Major v2 improvements:
    1. Better GitHub issue-template section extraction.
    2. Better linked PR selection.
    3. Separates raw solution from learning-ready solution.

Run from project root:
    python scripts/02_parse_issue_trajectory.py --repo OpenHands/OpenHands
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def repo_slug(repo: str) -> str:
    return repo.replace("/", "_")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[WRITE] {path}")


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if text.lower() in {"_no response_", "no response", "n/a", "none", "not applicable"}:
        return ""
    return text


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


SECTION_ALIASES: dict[str, list[str]] = {
    "bug_description": ["bug description", "description", "summary", "problem", "issue"],
    "expected_behavior": ["expected behavior", "expected", "what did you expect", "expected result"],
    "actual_behavior": ["actual behavior", "actual", "what happened", "current behavior", "observed behavior", "observed"],
    "reproduction_steps": ["steps to reproduce", "reproduction steps", "reproduction", "repro", "how to reproduce"],
    "environment": ["environment", "openhands installation method", "openhands version", "operating system", "browser", "model name", "system information", "version", "os", "platform"],
    "logs": ["logs and error messages", "logs", "error messages", "traceback", "stack trace"],
    "screenshots": ["screenshots and additional context", "screenshots", "additional context"],
}


def normalize_heading(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^#+\s*", "", line)
    line = line.strip("*").strip()
    line = re.sub(r":\s*$", "", line)
    return line.lower().strip()


def canonical_section_name(heading: str) -> str | None:
    norm = normalize_heading(heading)
    for field, aliases in SECTION_ALIASES.items():
        if norm in aliases:
            return field
    return None


def extract_sections(body: str) -> dict[str, str]:
    body = clean_text(body)
    result = {k: "" for k in SECTION_ALIASES}
    lines = body.splitlines()
    heading_indices: list[tuple[int, str]] = []

    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,6}\s+.+", line) or re.match(r"^\s*\*\*.+\*\*\s*:?\s*$", line):
            field = canonical_section_name(line)
            if field:
                heading_indices.append((i, field))

    if not heading_indices:
        return result

    for idx, (start_line, field) in enumerate(heading_indices):
        end_line = heading_indices[idx + 1][0] if idx + 1 < len(heading_indices) else len(lines)
        content = clean_text("\n".join(lines[start_line + 1:end_line]))
        if content and not result[field]:
            result[field] = content

    return result


def infer_problem(issue: dict[str, Any], sections: dict[str, str]) -> str:
    title = clean_text(issue.get("title", ""))
    bug_description = clean_text(sections.get("bug_description", ""))
    if bug_description:
        return clean_text(f"{title}\n\n{bug_description}")

    body = clean_text(issue.get("body", ""))
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    fallback = "\n\n".join(paragraphs[:3])
    return clean_text(f"{title}\n\n{fallback}")


def extract_pr_numbers_from_text(text: str) -> set[int]:
    return {int(m.group(1)) for m in re.finditer(r"/pull/(\d+)", text or "")}


def discover_pr_numbers(issue: dict[str, Any], timeline: list[dict[str, Any]]) -> set[int]:
    nums = set()
    nums.update(extract_pr_numbers_from_text(issue.get("body", "")))
    for c in issue.get("comments", []):
        nums.update(extract_pr_numbers_from_text(c.get("body", "")))
    for event in timeline:
        nums.update(extract_pr_numbers_from_text(json.dumps(event, ensure_ascii=False)))
    return nums


def tokenize(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "when", "then", "have", "has", "are", "was", "were", "can", "you", "your", "not", "all", "issue", "bug", "fix", "feat", "frontend", "backend", "openhands"}
    return {t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text or "") if t.lower() not in stop}


def contains_closing_reference(text: str, issue_number: int) -> bool:
    if not text:
        return False
    pattern = rf"(?i)\b(fix(?:es|ed)?|close(?:s|d)?|resolve(?:s|d)?)\s+(?:[^\n#]{{0,80}})?#\s*{issue_number}\b"
    if re.search(pattern, text):
        return True
    if re.search(rf"(?i)\b(fix(?:es|ed)?|close(?:s|d)?|resolve(?:s|d)?)\b[^\n]+/issues/{issue_number}\b", text):
        return True
    return False


def is_dependency_pr(pr: dict[str, Any]) -> bool:
    title = (pr.get("title") or "").lower()
    body = (pr.get("body") or "").lower()
    author = pr.get("author")
    author_login = author.get("login", "").lower() if isinstance(author, dict) else ""
    return "dependabot" in author_login or title.startswith("chore(deps)") or "bump " in title or "dependabot" in body[:1000]


def issue_is_dependency_related(issue: dict[str, Any]) -> bool:
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    return any(k in text for k in ["dependency", "dependencies", "dependabot", "version bump", "package"])


def files_match_issue_domain(issue: dict[str, Any], pr: dict[str, Any]) -> float:
    issue_text = f"{issue.get('title', '')}\n{issue.get('body', '')}".lower()
    files = [f.get("path", "") for f in pr.get("files", []) if isinstance(f, dict)]
    files_text = " ".join(files).lower()
    score = 0.0
    domain_pairs = [
        (["frontend", "ui", "viewer", "render", "settings", "basic", "advanced"], ["frontend/", ".tsx", ".ts"]),
        (["enterprise", "sharing", "endpoint", "authenticated"], ["enterprise/", "server/", "router", "service"]),
        (["test", "ci", "pytest"], ["test", "__tests__", ".test.", "pytest"]),
        (["docs", "readme", "documentation"], ["docs/", "readme", ".md"]),
        (["config", "settings", "yaml", "toml"], ["settings", "config", ".yaml", ".toml", ".json"]),
    ]
    for issue_keywords, file_keywords in domain_pairs:
        if any(k in issue_text for k in issue_keywords) and any(k in files_text for k in file_keywords):
            score += 2.0
    return score


def pr_issue_keyword_overlap(issue: dict[str, Any], pr: dict[str, Any]) -> float:
    issue_tokens = tokenize(f"{issue.get('title', '')}\n{issue.get('body', '')}")
    pr_tokens = tokenize(f"{pr.get('title', '')}\n{pr.get('body', '')}")
    if not issue_tokens or not pr_tokens:
        return 0.0
    return min(4.0, len(issue_tokens & pr_tokens) * 0.4)


def temporal_score(issue: dict[str, Any], pr: dict[str, Any]) -> float:
    issue_created = parse_dt(issue.get("createdAt"))
    pr_created = parse_dt(pr.get("createdAt"))
    if not issue_created or not pr_created:
        return 0.0
    delta_days = (pr_created - issue_created).total_seconds() / 86400.0
    if -1 <= delta_days <= 30:
        return 2.0
    if delta_days < -30:
        return -5.0
    if delta_days < -1:
        return -1.0
    if delta_days > 365:
        return -1.0
    return 0.5


def score_pr_for_issue(issue: dict[str, Any], pr: dict[str, Any]) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    body = pr.get("body") or ""
    title = pr.get("title") or ""
    combined = f"{title}\n{body}"
    issue_number = int(issue["number"])

    if contains_closing_reference(combined, issue_number):
        score += 8.0
        reasons.append("explicit_closing_reference")

    if pr.get("mergedAt"):
        score += 3.0
        reasons.append("merged_pr")
    elif str(pr.get("state", "")).upper() == "CLOSED":
        score -= 1.0
        reasons.append("closed_unmerged_pr")

    overlap = pr_issue_keyword_overlap(issue, pr)
    if overlap:
        score += overlap
        reasons.append(f"title_body_keyword_overlap:{overlap:.1f}")

    domain = files_match_issue_domain(issue, pr)
    if domain:
        score += domain
        reasons.append(f"changed_files_match_issue_domain:{domain:.1f}")

    t_score = temporal_score(issue, pr)
    if t_score:
        score += t_score
        reasons.append(f"temporal_score:{t_score:.1f}")

    if is_dependency_pr(pr) and not issue_is_dependency_related(issue):
        score -= 8.0
        reasons.append("dependency_pr_penalty")

    if re.search(rf"(?i)\brelated\b[^\n]+/pull/{pr.get('number')}\b", issue.get("body", "")):
        score -= 2.0
        reasons.append("related_pr_penalty")

    return score, reasons


def select_best_solution_pr(issue: dict[str, Any], prs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not prs:
        return None
    scored = []
    for pr in prs:
        score, reasons = score_pr_for_issue(issue, pr)
        scored.append((score, reasons, pr))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_reasons, best_pr = scored[0]
    best_pr = dict(best_pr)
    best_pr["_selection_score"] = best_score
    best_pr["_selection_reasons"] = best_reasons
    best_pr["_all_candidate_scores"] = [
        {"number": p.get("number"), "title": p.get("title"), "score": s, "reasons": r, "merged_at": p.get("mergedAt"), "state": p.get("state")}
        for s, r, p in scored
    ]
    return best_pr


def comment_is_feedback(comment: dict[str, Any]) -> bool:
    text = (comment.get("body") or "").lower()
    keywords = ["doesn't work", "does not work", "failed", "error", "missing", "please", "can you", "could you", "should", "needs", "regression", "test", "fix", "reproduce", "expected", "actual", "confirmed", "this is actually done", "approved", "request changes", "nit", "lgtm"]
    return any(k in text for k in keywords)


def extract_issue_feedback(issue: dict[str, Any]) -> list[dict[str, Any]]:
    feedback = []
    for c in issue.get("comments", []):
        if comment_is_feedback(c):
            feedback.append({
                "author": c.get("author", {}).get("login") if isinstance(c.get("author"), dict) else c.get("author"),
                "created_at": c.get("createdAt"),
                "body": clean_text(c.get("body", "")),
                "source": "issue_comment",
            })
    return feedback


def extract_pr_feedback(pr: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not pr:
        return []
    feedback = []
    for r in pr.get("reviews", []) or []:
        body = clean_text(r.get("body", ""))
        state = r.get("state")
        if body or state:
            feedback.append({
                "author": r.get("author", {}).get("login") if isinstance(r.get("author"), dict) else r.get("author"),
                "created_at": r.get("submittedAt") or r.get("createdAt"),
                "state": state,
                "body": body,
                "source": "pr_review",
            })
    for c in pr.get("comments", []) or []:
        body = clean_text(c.get("body", ""))
        if body and comment_is_feedback(c):
            feedback.append({
                "author": c.get("author", {}).get("login") if isinstance(c.get("author"), dict) else c.get("author"),
                "created_at": c.get("createdAt"),
                "body": body,
                "source": "pr_comment",
            })
    return feedback


def extract_testing_lines(text: str) -> list[str]:
    lines = []
    in_testing = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if re.match(r"^#{1,6}\s*(testing|how to test)\b", lower):
            in_testing = True
            continue
        if in_testing and re.match(r"^#{1,6}\s+", stripped):
            break
        if in_testing and stripped:
            lines.append(stripped)
    for line in (text or "").splitlines():
        stripped = line.strip()
        if any(cmd in stripped for cmd in ["npm run", "pytest", "make ", "cd frontend", "ruff", "mypy"]):
            if stripped not in lines:
                lines.append(stripped)
    return lines[:20]


def extract_summary_bullets(text: str) -> list[str]:
    lines = (text or "").splitlines()
    bullets = []
    in_summary = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if re.match(r"^#{1,6}\s*(summary|changes|description|why)\b", lower):
            in_summary = True
            continue
        if in_summary and re.match(r"^#{1,6}\s+", stripped):
            break
        if in_summary and re.match(r"^[-*]\s+", stripped):
            bullets.append(re.sub(r"^[-*]\s+", "", stripped))
    return bullets[:10]


def build_solution(best_pr: dict[str, Any] | None) -> dict[str, Any]:
    if not best_pr:
        return {
            "solution_raw": {"text": "", "source": "none", "confidence": 0.0},
            "solution_summary": {
                "selected_pr": None,
                "fix_summary": "",
                "changed_files": [],
                "tests": [],
                "selection_score": 0.0,
                "selection_reasons": [],
                "candidate_scores": [],
            },
        }

    files = [f.get("path") for f in best_pr.get("files", []) if isinstance(f, dict)]
    body = best_pr.get("body") or ""
    title = best_pr.get("title") or ""
    raw_text = clean_text(f"PR #{best_pr.get('number')}: {title}\n\n{body}\n\nChanged files: {', '.join(files[:30])}")
    bullets = extract_summary_bullets(body)
    tests = extract_testing_lines(body)
    fix_summary = "; ".join(bullets) if bullets else title

    confidence = 0.55
    if best_pr.get("mergedAt"):
        confidence += 0.2
    if "explicit_closing_reference" in best_pr.get("_selection_reasons", []):
        confidence += 0.15
    if best_pr.get("_selection_score", 0.0) >= 8.0:
        confidence += 0.1
    confidence = min(confidence, 0.98)

    return {
        "solution_raw": {"text": raw_text, "source": f"pr:{best_pr.get('number')}", "confidence": confidence},
        "solution_summary": {
            "selected_pr": best_pr.get("number"),
            "title": title,
            "fix_summary": fix_summary,
            "changed_files": files[:30],
            "tests": tests,
            "merged_at": best_pr.get("mergedAt"),
            "selection_score": best_pr.get("_selection_score", 0.0),
            "selection_reasons": best_pr.get("_selection_reasons", []),
            "candidate_scores": best_pr.get("_all_candidate_scores", []),
        },
    }


def parse_one(repo: str, issue_path: Path, project_root: Path) -> dict[str, Any]:
    slug = repo_slug(repo)
    issue = load_json(issue_path)
    issue_num = issue["number"]
    timeline_path = project_root / "data" / "raw" / "timelines" / f"{slug}_{issue_num}.json"
    timeline = load_json(timeline_path) if timeline_path.exists() else []

    pr_numbers = discover_pr_numbers(issue, timeline)
    prs, pr_paths = [], []
    for n in sorted(pr_numbers):
        pr_path = project_root / "data" / "raw" / "prs" / f"{slug}_{n}.json"
        if pr_path.exists():
            prs.append(load_json(pr_path))
            pr_paths.append(str(pr_path))

    sections = extract_sections(issue.get("body", ""))
    best_pr = select_best_solution_pr(issue, prs)
    solution = build_solution(best_pr)
    all_feedback = extract_issue_feedback(issue) + extract_pr_feedback(best_pr)

    quality_flags = []
    if not issue.get("body"):
        quality_flags.append("missing_issue_body")
    if not prs:
        quality_flags.append("missing_linked_pr")
    if not best_pr:
        quality_flags.append("missing_selected_solution_pr")
    if not solution["solution_summary"].get("fix_summary"):
        quality_flags.append("missing_solution_summary")
    if not all_feedback:
        quality_flags.append("missing_feedback")
    if not sections.get("reproduction_steps"):
        quality_flags.append("missing_reproduction_steps")
    if best_pr and solution["solution_summary"].get("selection_score", 0.0) < 5.0:
        quality_flags.append("low_solution_pr_selection_confidence")

    labels = [l.get("name", "") if isinstance(l, dict) else str(l) for l in issue.get("labels", [])]
    extracted_confidence = solution["solution_raw"]["confidence"]
    if all_feedback:
        extracted_confidence = min(0.99, extracted_confidence + 0.05)
    if "low_solution_pr_selection_confidence" in quality_flags:
        extracted_confidence = min(extracted_confidence, 0.55)

    return {
        "repo": repo,
        "issue_number": issue_num,
        "url": issue.get("url"),
        "title": issue.get("title"),
        "state": issue.get("state"),
        "labels": labels,
        "created_at": issue.get("createdAt"),
        "closed_at": issue.get("closedAt"),
        "raw_refs": {"issue": str(issue_path), "timeline": str(timeline_path) if timeline_path.exists() else None, "prs": pr_paths},
        "raw_problem": {"title": issue.get("title"), "body": issue.get("body"), "labels": labels, "author": issue.get("author")},
        "conversation": [
            {"type": "issue_body", "author": issue.get("author"), "created_at": issue.get("createdAt"), "body": clean_text(issue.get("body", ""))}
        ] + [
            {"type": "comment", "author": c.get("author"), "created_at": c.get("createdAt"), "body": clean_text(c.get("body", ""))}
            for c in issue.get("comments", [])
        ],
        "linked_prs": [
            {
                "number": p.get("number"),
                "title": p.get("title"),
                "url": p.get("url"),
                "state": p.get("state"),
                "merged_at": p.get("mergedAt"),
                "changed_files": [f.get("path") for f in p.get("files", []) if isinstance(f, dict)],
                "review_count": len(p.get("reviews", []) or []),
                "comment_count": len(p.get("comments", []) or []),
                "selection_score": score_pr_for_issue(issue, p)[0],
                "selection_reasons": score_pr_for_issue(issue, p)[1],
            }
            for p in prs
        ],
        "extracted": {
            "problem": infer_problem(issue, sections),
            "expected_behavior": clean_text(sections.get("expected_behavior", "")),
            "actual_behavior": clean_text(sections.get("actual_behavior", "")),
            "reproduction_steps": clean_text(sections.get("reproduction_steps", "")),
            "environment": clean_text(sections.get("environment", "")),
            "logs": clean_text(sections.get("logs", "")),
            "solution": solution["solution_raw"],
            "solution_summary": solution["solution_summary"],
            "feedback": all_feedback,
            "confidence": extracted_confidence,
        },
        "quality_flags": quality_flags,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse raw GitHub issue artifacts into normalized trajectories.")
    parser.add_argument("--repo", required=True, help='Repo in "owner/name" format.')
    args = parser.parse_args()
    project_root = Path.cwd()
    slug = repo_slug(args.repo)
    issue_dir = project_root / "data" / "raw" / "issues"
    out_dir = project_root / "data" / "processed" / "trajectories"
    paths = sorted(issue_dir.glob(f"{slug}_*.json"))
    if not paths:
        raise RuntimeError(f"No raw issues found for {args.repo} under {issue_dir}")
    for p in paths:
        traj = parse_one(args.repo, p, project_root)
        write_json(out_dir / f"{slug}_{traj['issue_number']}.json", traj)
    print(f"\n[DONE] Parsed {len(paths)} trajectories.")


if __name__ == "__main__":
    main()
