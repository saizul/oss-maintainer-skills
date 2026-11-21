#!/usr/bin/env python3
"""Turn an exported issue list into a triage queue.

Input is the JSON printed by the GitHub CLI (no network access here):

  gh issue list --state open --limit 500 \
    --json number,title,body,labels,author,createdAt,updatedAt,comments,url > issues.json
  triage_report.py issues.json [--stale-days 60] [--markdown | --json]

Buckets: untriaged, needs-info overdue, bug reports missing reproduction
details, possible duplicates, stale, and good-first-issue candidates.

Exit codes: 0 = ok, 1 = --fail-on-untriaged and untriaged issues exist, 2 = usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import re
import sys
from pathlib import Path

TRIAGED_PREFIXES = ("type:", "status: confirmed", "priority:", "area:")
TRIAGED_NAMES = {
    "bug",
    "enhancement",
    "documentation",
    "question",
    "confirmed",
    "duplicate",
    "invalid",
    "wontfix",
    "good first issue",
    "help wanted",
}
UNTRIAGED_NAMES = {"needs-triage", "needs triage", "status: needs triage", "triage"}
NEEDS_INFO_NAMES = {
    "needs-info",
    "needs info",
    "status: needs info",
    "needs-repro",
    "status: needs repro",
    "waiting for author",
}
BUG_NAMES = {"bug", "type: bug"}
REPRO_HINTS = re.compile(
    r"(steps to reproduce|to reproduce|reproduc|expected|actual|version|traceback|stack trace|```|minimal example)",
    re.I,
)
STOPWORDS = {"the", "a", "an", "is", "in", "on", "of", "to", "and", "for", "with", "when", "not", "does", "error"}


def parse_time(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def label_names(issue: dict) -> set[str]:
    out = set()
    for label in issue.get("labels") or []:
        name = label.get("name") if isinstance(label, dict) else label
        if isinstance(name, str):
            out.add(name.strip().lower())
    return out


def comment_count(issue: dict) -> int:
    c = issue.get("comments", 0)
    if isinstance(c, list):
        return len(c)
    if isinstance(c, dict):
        return int(c.get("totalCount", 0))
    return int(c or 0)


def is_triaged(labels: set[str]) -> bool:
    if labels & UNTRIAGED_NAMES:
        return False
    return bool(labels & TRIAGED_NAMES) or any(lbl.startswith(TRIAGED_PREFIXES) for lbl in labels)


def normalise_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(w for w in words if w not in STOPWORDS)


def find_duplicates(issues: list[dict], threshold: float) -> list[tuple[int, int, float]]:
    pairs = []
    norm = [(i["number"], normalise_title(i.get("title", ""))) for i in issues]
    for a in range(len(norm)):
        for b in range(a + 1, len(norm)):
            na, ta = norm[a]
            nb, tb = norm[b]
            if not ta or not tb:
                continue
            ratio = difflib.SequenceMatcher(None, ta, tb).ratio()
            if ratio >= threshold:
                pairs.append((min(na, nb), max(na, nb), round(ratio, 2)))
    return sorted(pairs)


def gfi_candidate(issue: dict, labels: set[str]) -> bool:
    if "good first issue" in labels or (labels & BUG_NAMES and "confirmed" not in labels):
        return False
    body = issue.get("body") or ""
    small = len(body) < 1500 and comment_count(issue) <= 3
    docs = bool(labels & {"documentation", "type: documentation"}) or re.search(
        r"\b(typo|docs?|readme|spelling)\b", issue.get("title", ""), re.I
    )
    return bool(small and docs)


def build(issues: list[dict], now: dt.datetime, stale_days: int, info_days: int, dup_threshold: float) -> dict:
    report: dict[str, list] = {
        "untriaged": [],
        "needs_info_overdue": [],
        "missing_repro": [],
        "possible_duplicates": [],
        "stale": [],
        "good_first_issue_candidates": [],
    }
    for issue in issues:
        if issue.get("pullRequest") or issue.get("isPullRequest"):
            continue
        labels = label_names(issue)
        updated = parse_time(issue.get("updatedAt") or issue.get("createdAt"))
        idle = (now - updated).days
        entry = {
            "number": issue.get("number"),
            "title": issue.get("title", ""),
            "url": issue.get("url", ""),
            "idle_days": idle,
            "labels": sorted(labels),
        }
        if not is_triaged(labels):
            report["untriaged"].append(entry)
        if labels & NEEDS_INFO_NAMES and idle >= info_days:
            report["needs_info_overdue"].append(entry)
        if labels & BUG_NAMES and not REPRO_HINTS.search(issue.get("body") or ""):
            report["missing_repro"].append(entry)
        if idle >= stale_days and "pinned" not in labels and not labels & {"security", "priority: critical"}:
            report["stale"].append(entry)
        if gfi_candidate(issue, labels):
            report["good_first_issue_candidates"].append(entry)
    for a, b, ratio in find_duplicates([i for i in issues if not i.get("pullRequest")], dup_threshold):
        report["possible_duplicates"].append({"issues": [a, b], "similarity": ratio})
    for key in ("untriaged", "missing_repro", "good_first_issue_candidates"):
        report[key].sort(key=lambda e: e["number"] or 0)
    for key in ("needs_info_overdue", "stale"):
        report[key].sort(key=lambda e: -e["idle_days"])
    return {"total_open": len(issues), "generated_at": now.isoformat(), **report}


TITLES = {
    "untriaged": ("Untriaged", "Label (type + priority), reproduce or ask for info. Reply within 72 hours."),
    "needs_info_overdue": (
        "Waiting on reporter, overdue",
        "Post a final nudge; close with the 'needs-info' close reply if still silent.",
    ),
    "missing_repro": (
        "Bug reports without reproduction details",
        "Ask for version, steps and expected vs actual (reply template 'needs-repro').",
    ),
    "possible_duplicates": (
        "Possible duplicates",
        "Compare and close the newer one with the duplicate reply, linking the original.",
    ),
    "stale": ("Stale", "Decide: still wanted? Label 'help wanted', or close with the stale reply."),
    "good_first_issue_candidates": (
        "Good first issue candidates",
        "Rewrite with context, files to touch and acceptance criteria, then label.",
    ),
}


def format_report(report: dict, markdown: bool) -> str:
    lines = [f"{'# ' if markdown else ''}Triage report: {report['total_open']} open issue(s)", ""]
    for key, (title, action) in TITLES.items():
        items = report[key]
        lines.append(f"{'## ' if markdown else ''}{title} ({len(items)})")
        if items:
            lines.append(f"{'> ' if markdown else '  '}Next: {action}")
        for e in items:
            if key == "possible_duplicates":
                a, b = e["issues"]
                lines.append(f"- #{a} and #{b} (title similarity {e['similarity']})")
            else:
                idle = f", idle {e['idle_days']}d" if key in ("stale", "needs_info_overdue") else ""
                lines.append(f"- #{e['number']} {e['title']}{idle}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a triage queue from `gh issue list --json` output.")
    parser.add_argument("file", help="issues JSON file, or - for stdin")
    parser.add_argument(
        "--stale-days", type=int, default=60, help="idle days before an issue counts as stale (default 60)"
    )
    parser.add_argument(
        "--info-days", type=int, default=14, help="days to wait for a reporter before closing (default 14)"
    )
    parser.add_argument(
        "--dup-threshold", type=float, default=0.85, help="title similarity for duplicates, 0-1 (default 0.85)"
    )
    parser.add_argument("--now", help="ISO timestamp to use as 'now' (for reproducible reports)")
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="print JSON")
    fmt.add_argument("--markdown", action="store_true", help="print markdown (for a tracking issue)")
    parser.add_argument("--fail-on-untriaged", action="store_true", help="exit 1 if any issue is untriaged")
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text(encoding="utf-8")
        issues = json.loads(raw)
        if not isinstance(issues, list):
            raise ValueError("expected a JSON array of issues")
        now = parse_time(args.now) if args.now else dt.datetime.now(dt.UTC)
        report = build(issues, now, args.stale_days, args.info_days, args.dup_threshold)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(report, indent=2) if args.json else format_report(report, args.markdown),
        end="" if not args.json else "\n",
    )
    return 1 if args.fail_on_untriaged and report["untriaged"] else 0


if __name__ == "__main__":
    sys.exit(main())
