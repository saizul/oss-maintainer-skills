#!/usr/bin/env python3
"""Compute the next semantic version and a changelog section from Conventional Commits.

Commit sources (pick one):
  --git              read commits since the latest tag with `git log` (read-only)
  --input FILE       a file of commit subjects, one per line, or records produced by
                     git log --format='%H%x1f%s%x1f%b%x1e'
  (default)          the same formats on stdin

Exit codes: 0 = ok, 1 = no releasable commits and --fail-if-none was given,
2 = usage error (bad version, not a git repository, ...).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SEMVER = re.compile(
    r"^v?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)
HEADER = re.compile(r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^()]*)\))?(?P<bang>!)?: (?P<subject>.+)$")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: (.+)", re.M)
GIT_REVERT = re.compile(r'^Revert "(?P<header>.+)"$')
PR_REF = re.compile(r"\(#(\d+)\)")

SECTIONS = [
    ("breaking", "Breaking changes"),
    ("feat", "Features"),
    ("fix", "Bug fixes"),
    ("perf", "Performance"),
    ("revert", "Reverts"),
    ("docs", "Documentation"),
    ("other", "Other changes"),
]
HIDDEN_BY_DEFAULT = {"docs", "other"}
BUMP_RANK = {"none": 0, "patch": 1, "minor": 2, "major": 3}


@dataclass
class Commit:
    hash: str
    type: str
    scope: str
    subject: str
    breaking: bool
    breaking_note: str
    conventional: bool


def parse_commit(sha: str, header: str, body: str = "") -> Commit:
    footer = BREAKING_FOOTER.search(body or "")
    reverted = GIT_REVERT.match(header.strip())
    if reverted:
        # `git revert` writes: Revert "feat(api): add x". Treat it as a revert commit; the
        # subject keeps the reverted header so the changelog says what was undone.
        return Commit(sha, "revert", "", reverted.group("header").strip(), False, "", True)
    m = HEADER.match(header.strip())
    if not m:
        return Commit(sha, "other", "", header.strip(), bool(footer), footer.group(1) if footer else "", False)
    breaking = bool(m.group("bang")) or bool(footer)
    note = footer.group(1).strip() if footer else (m.group("subject") if m.group("bang") else "")
    return Commit(
        sha, m.group("type").lower(), (m.group("scope") or "").strip(), m.group("subject").strip(), breaking, note, True
    )


def parse_log(text: str) -> list[Commit]:
    commits = []
    if "\x1e" in text:
        for record in text.split("\x1e"):
            record = record.strip("\n")
            if not record.strip():
                continue
            parts = record.split("\x1f")
            sha = parts[0].strip()
            header = parts[1] if len(parts) > 1 else ""
            body = parts[2] if len(parts) > 2 else ""
            if header.strip():
                commits.append(parse_commit(sha, header, body))
    else:
        for line in text.splitlines():
            if line.strip():
                commits.append(parse_commit("", line))
    return commits


def is_skipped(c: Commit) -> bool:
    s = c.subject.lower()
    return (c.type == "chore" and (c.scope == "release" or s.startswith("release"))) or c.subject.startswith("Merge ")


def bump_for(commits: list[Commit]) -> str:
    level = "none"
    for c in commits:
        if c.breaking:
            this = "major"
        elif c.type == "feat":
            this = "minor"
        elif c.type in ("fix", "perf", "revert"):
            this = "patch"
        else:
            this = "none"
        if BUMP_RANK[this] > BUMP_RANK[level]:
            level = this
    return level


def parse_version(v: str) -> tuple[int, int, int, str | None]:
    m = SEMVER.match(v.strip())
    if not m:
        raise ValueError(f"not a semantic version: {v!r}")
    return int(m["major"]), int(m["minor"]), int(m["patch"]), m["pre"]


def next_version(current: str, bump: str, pre: str | None = None, zero_major_rule: bool = True) -> str:
    major, minor, patch, cur_pre = parse_version(current)
    if bump == "none":
        return f"{major}.{minor}.{patch}" + (f"-{cur_pre}" if cur_pre else "")
    if zero_major_rule and major == 0 and bump == "major":
        # SemVer item 4: 0.y.z is initial development, so a breaking change
        # bumps the minor version until you deliberately release 1.0.0.
        bump = "minor"
    if cur_pre:
        # Continue or finish a prerelease when it already carries this bump:
        # 1.2.0-rc.1 + feat -> 1.2.0 (or 1.2.0-rc.2 with --pre rc).
        carries = (bump == "major" and minor == 0 and patch == 0) or (bump == "minor" and patch == 0) or bump == "patch"
        if carries:
            base = f"{major}.{minor}.{patch}"
            if not pre:
                return base
            m = re.fullmatch(re.escape(pre) + r"\.(\d+)", cur_pre)
            if m:
                return f"{base}-{pre}.{int(m.group(1)) + 1}"
            return f"{base}-{pre}.1"
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    version = f"{major}.{minor}.{patch}"
    if pre:
        version += f"-{pre}.1"
    return version


def changelog(version: str, commits: list[Commit], date: str, repo_url: str | None, include: set[str]) -> str:
    groups: dict[str, list[Commit]] = {key: [] for key, _ in SECTIONS}
    for c in commits:
        if c.breaking:
            groups["breaking"].append(c)
        key = c.type if c.type in groups and c.type != "breaking" else "other"
        if c.type in ("chore", "ci", "build", "style", "test", "refactor"):
            key = "other"
        groups[key].append(c)
    lines = [f"## [{version}] - {date}", ""]
    for key, title in SECTIONS:
        items = groups[key]
        if not items or (key in HIDDEN_BY_DEFAULT and key not in include):
            continue
        lines.append(f"### {title}")
        lines.append("")
        for c in items:
            text = c.breaking_note if key == "breaking" and c.breaking_note else c.subject
            scope = f"**{c.scope}:** " if c.scope else ""
            ref = ""
            if c.hash:
                short = c.hash[:7]
                ref = f" ([{short}]({repo_url.rstrip('/')}/commit/{c.hash}))" if repo_url else f" ({short})"
            if repo_url:
                text = PR_REF.sub(rf"([#\1]({repo_url.rstrip('/')}/pull/\1))", text)
            lines.append(f"- {scope}{text}{ref}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def latest_tag(cwd: Path) -> str | None:
    try:
        return git(["describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"], cwd).strip() or None
    except subprocess.CalledProcessError:
        try:
            return git(["describe", "--tags", "--abbrev=0", "--match", "[0-9]*"], cwd).strip() or None
        except subprocess.CalledProcessError:
            return None


def git_commits(cwd: Path, since: str | None) -> str:
    rng = [f"{since}..HEAD"] if since else ["HEAD"]
    return git(["log", "--no-merges", "--format=%H%x1f%s%x1f%b%x1e", *rng], cwd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Next semver + changelog section from Conventional Commits.")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--git", action="store_true", help="read commits from git since the latest tag")
    src.add_argument("--input", help="file with commit subjects (one per line) or git log records")
    parser.add_argument("--repo-dir", default=".", help="repository for --git (default: .)")
    parser.add_argument("--since", help="tag or ref to start from (default with --git: latest v* tag)")
    parser.add_argument("--current", help="current version (default: latest tag, else 0.0.0)")
    parser.add_argument("--pre", help="prerelease id, e.g. rc or beta -> 1.3.0-rc.1")
    parser.add_argument("--no-zero-major-rule", action="store_true", help="allow 0.x -> 1.0.0 on a breaking change")
    parser.add_argument("--repo-url", help="https://github.com/OWNER/NAME, to link commit hashes")
    parser.add_argument("--date", help="release date (default: today, UTC)")
    parser.add_argument("--include", default="", help="also list these hidden groups: docs,other")
    parser.add_argument("--json", action="store_true", help="print JSON instead of markdown")
    parser.add_argument("--fail-if-none", action="store_true", help="exit 1 when nothing warrants a release")
    args = parser.parse_args(argv)

    repo = Path(args.repo_dir)
    tag = None
    try:
        if args.git:
            tag = args.since or latest_tag(repo)
            text = git_commits(repo, tag)
        elif args.input:
            text = Path(args.input).read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
    except (OSError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"error: cannot read commits: {exc}", file=sys.stderr)
        return 2

    current = args.current or (tag if tag and SEMVER.match(tag) else None) or "0.0.0"
    try:
        parse_version(current)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    commits = [c for c in parse_log(text) if not is_skipped(c)]
    bump = bump_for(commits)
    new = next_version(current, bump, args.pre, not args.no_zero_major_rule)
    date = args.date or dt.datetime.now(dt.UTC).date().isoformat()
    include = {s.strip() for s in args.include.split(",") if s.strip()}
    notes = changelog(new, commits, date, args.repo_url, include) if bump != "none" else ""

    if args.json:
        print(
            json.dumps(
                {
                    "current": current.lstrip("v"),
                    "bump": bump,
                    "next": new,
                    "tag": f"v{new}",
                    "commits": len(commits),
                    "non_conventional": [c.subject for c in commits if not c.conventional],
                    "changelog": notes,
                    "parsed": [asdict(c) for c in commits],
                },
                indent=2,
            )
        )
    else:
        print(f"current: {current.lstrip('v')}\nbump:    {bump}\nnext:    {new}\n")
        if notes:
            print(notes, end="")
        else:
            print("No feat, fix, perf, revert or breaking commits since the last release; nothing to release.")
        nonconv = [c.subject for c in commits if not c.conventional]
        if nonconv:
            print(
                f"\nnote: {len(nonconv)} commit(s) do not follow Conventional Commits and were listed as 'other'.",
                file=sys.stderr,
            )
    return 1 if args.fail_if_none and bump == "none" else 0


if __name__ == "__main__":
    sys.exit(main())
