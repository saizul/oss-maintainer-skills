#!/usr/bin/env python3
"""Score the health of a local open-source repository and print concrete fixes.

Read-only: the script only reads files below the given path. It never runs git,
never touches the network and never writes anything.

Exit codes: 0 = score is at or above --min-score (default 0), 1 = below it,
2 = usage error (for example the path does not exist).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# GitHub looks for community health files in the root, docs/ and .github/.
COMMUNITY_DIRS = ("", "docs", ".github")
SKIP_DIRS = {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "__pycache__"}


@dataclass
class Check:
    id: str
    title: str
    max_points: int
    points: int = 0
    fix: str = ""
    details: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.points >= self.max_points


def find_file(root: Path, stems: tuple[str, ...], dirs: tuple[str, ...] = COMMUNITY_DIRS) -> Path | None:
    """Return the first file whose name (case-insensitive, any extension) matches a stem."""
    wanted = {s.lower() for s in stems}
    for d in dirs:
        base = root / d if d else root
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if not p.is_file():
                continue
            name = p.name.lower()
            stem = name.split(".", 1)[0]
            if name in wanted or stem in wanted:
                return p
    return None


def read_text(path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def headings(markdown: str) -> list[str]:
    out = []
    in_code = False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if not in_code:
            m = re.match(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m:
                out.append(m.group(1).lower())
    return out


def has_heading(hs: list[str], *words: str) -> bool:
    return any(any(w in h for w in words) for h in hs)


def walk_files(root: Path, max_depth: int = 4):
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name not in SKIP_DIRS and depth < max_depth:
                    stack.append((p, depth + 1))
            elif p.is_file():
                yield p


def check_readme(root: Path) -> tuple[Check, Check, Check, str]:
    readme_path = find_file(root, ("readme",), ("", ".github", "docs"))
    text = read_text(readme_path)
    exists = Check("readme", "README exists and is substantial", 10)
    if readme_path is None:
        exists.fix = "Add a README.md with a one-line pitch, install steps and a quick start example."
    else:
        words = len(text.split())
        exists.details.append(f"{readme_path.relative_to(root)} ({words} words)")
        if words >= 150:
            exists.points = 10
        else:
            exists.points = 5
            exists.fix = (
                f"README has only {words} words; explain what the project does, who it is for and how to start."
            )

    sections = Check("readme-sections", "README covers install, usage, contributing and license", 15)
    if text:
        hs = headings(text)
        parts = [
            (4, ("install", "getting started", "setup", "quick start", "quickstart"), "an Installation section"),
            (
                4,
                ("usage", "example", "quick start", "quickstart", "how to use", "getting started"),
                "a Usage or Quick start section with a code example",
            ),
            (2, ("contribut",), "a Contributing section linking CONTRIBUTING.md"),
            (2, ("license", "licence"), "a License section"),
        ]
        missing = []
        for pts, words, label in parts:
            if has_heading(hs, *words):
                sections.points += pts
            else:
                missing.append(label)
        if "```" in text or "~~~" in text or re.search(r"^( {4}|\t)\S", text, re.M):
            sections.points += 3
        else:
            missing.append("at least one fenced code block (a copy-pasteable command)")
        if missing:
            sections.fix = "Add " + "; ".join(missing) + "."
    else:
        sections.fix = "Write a README first (see the readme-writer skill)."

    badges = Check("badges", "README shows status badges (CI, version, license)", 5)
    found = re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)", text)
    badge_hosts = ("shields.io", "badge", "/workflows/", "codecov", "badgen", "pepy", "readthedocs")
    n = sum(1 for url in found if any(h in url for h in badge_hosts))
    if n >= 2:
        badges.points = 5
    elif n == 1:
        badges.points = 3
        badges.fix = "Add more badges: CI status, latest release/package version and license."
    else:
        badges.fix = "Add badges under the title: CI status, latest version and license (shields.io)."
    badges.details.append(f"{n} badge(s) found")
    return exists, sections, badges, text


def check_simple(root: Path, cid: str, title: str, pts: int, stems: tuple[str, ...], fix: str) -> Check:
    c = Check(cid, title, pts)
    p = find_file(root, stems)
    if p is not None and p.stat().st_size > 0:
        c.points = pts
        c.details.append(str(p.relative_to(root)))
    else:
        c.fix = fix
    return c


def check_license(root: Path) -> Check:
    c = Check("license", "LICENSE file", 10)
    p = find_file(root, ("license", "licence", "copying", "unlicense"), ("",))
    if p is None:
        c.fix = "Add a LICENSE file (MIT, Apache-2.0 or GPL-3.0 are common; https://choosealicense.com). Without one, nobody may legally reuse the code."
        return c
    text = read_text(p)
    c.details.append(str(p.relative_to(root)))
    if len(text.strip()) < 200:
        c.points = 5
        c.fix = "The LICENSE file looks truncated; paste the full license text."
    else:
        c.points = 10
    return c


def check_issue_templates(root: Path) -> Check:
    c = Check("issue-templates", "Issue templates (bug report, feature request)", 5)
    d = root / ".github" / "ISSUE_TEMPLATE"
    files = (
        [p for p in d.glob("*") if p.suffix.lower() in {".md", ".yml", ".yaml"} and p.name != "config.yml"]
        if d.is_dir()
        else []
    )
    legacy = find_file(root, ("issue_template",))
    if len(files) >= 2:
        c.points = 5
    elif files or legacy:
        c.points = 3
        c.fix = "Add both a bug report and a feature request template in .github/ISSUE_TEMPLATE/ (issue forms, .yml)."
    else:
        c.fix = "Add .github/ISSUE_TEMPLATE/bug_report.yml and feature_request.yml issue forms."
    c.details.extend(sorted(p.name for p in files))
    return c


def check_pr_template(root: Path) -> Check:
    c = Check("pr-template", "Pull request template", 4)
    p = find_file(root, ("pull_request_template",))
    if p is None and (root / ".github" / "PULL_REQUEST_TEMPLATE").is_dir():
        p = root / ".github" / "PULL_REQUEST_TEMPLATE"
    if p is not None:
        c.points = 4
        c.details.append(str(p.relative_to(root)))
    else:
        c.fix = "Add .github/pull_request_template.md with a summary prompt and a checklist (tests, docs, changelog)."
    return c


CI_PATHS = (
    ".gitlab-ci.yml",
    ".travis.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    ".circleci/config.yml",
    "bitbucket-pipelines.yml",
    ".woodpecker.yml",
)


def check_ci(root: Path) -> Check:
    c = Check("ci", "Continuous integration", 10)
    wf = root / ".github" / "workflows"
    found = sorted(p.name for p in wf.glob("*") if p.suffix in {".yml", ".yaml"}) if wf.is_dir() else []
    found += [p for p in CI_PATHS if (root / p).exists()]
    if found:
        c.points = 10
        c.details.extend(found)
    else:
        c.fix = "Add a CI workflow that runs lint and tests on every pull request (see the github-actions-ci skill)."
    return c


TEST_FILE = re.compile(r"(^test_.*\.py$|_test\.py$|_test\.go$|\.(test|spec)\.[cm]?[jt]sx?$|Test\.php$|_spec\.rb$)")


def check_tests(root: Path) -> Check:
    c = Check("tests", "Automated tests", 10)
    dirs = [d for d in ("tests", "test", "__tests__", "spec", "t") if (root / d).is_dir()]
    files = [p for p in walk_files(root) if TEST_FILE.search(p.name)]
    if dirs or files:
        c.points = 10
        c.details.extend(dirs)
        c.details.append(f"{len(files)} test file(s)")
    else:
        c.fix = "Add a tests/ directory with at least one test for the main feature and run it in CI."
    return c


def check_dependency_updates(root: Path) -> Check:
    c = Check("dependency-updates", "Automated dependency updates (Dependabot or Renovate)", 4)
    candidates = [
        root / ".github" / "dependabot.yml",
        root / ".github" / "dependabot.yaml",
        root / "renovate.json",
        root / "renovate.json5",
        root / ".github" / "renovate.json",
        root / ".renovaterc",
        root / ".renovaterc.json",
    ]
    hit = [p for p in candidates if p.exists()]
    if hit:
        c.points = 4
        c.details.append(str(hit[0].relative_to(root)))
    else:
        c.fix = "Add .github/dependabot.yml (see the security-policy skill: gen_security.py dependabot)."
    return c


def run_checks(root: Path) -> list[Check]:
    readme, sections, badges, _ = check_readme(root)
    return [
        readme,
        sections,
        badges,
        check_license(root),
        check_simple(
            root,
            "contributing",
            "CONTRIBUTING guide",
            8,
            ("contributing",),
            "Add CONTRIBUTING.md: dev setup, how to run tests, coding style, PR process (see contributor-onboarding).",
        ),
        check_simple(
            root,
            "code-of-conduct",
            "Code of conduct",
            5,
            ("code_of_conduct", "code-of-conduct"),
            "Add CODE_OF_CONDUCT.md (Contributor Covenant 2.1) with a private contact for reports.",
        ),
        check_simple(
            root,
            "security",
            "Security policy",
            7,
            ("security",),
            "Add SECURITY.md with supported versions and a private reporting channel (see the security-policy skill).",
        ),
        check_issue_templates(root),
        check_pr_template(root),
        check_ci(root),
        check_tests(root),
        check_simple(
            root,
            "changelog",
            "Changelog",
            4,
            ("changelog", "changes", "history", "news"),
            "Add CHANGELOG.md (Keep a Changelog format) and update it in every release.",
        ),
        check_simple(
            root,
            "gitignore",
            ".gitignore",
            3,
            (".gitignore",),
            "Add a .gitignore for your language (https://github.com/github/gitignore).",
        ),
        check_dependency_updates(root),
    ]


def grade(score: int) -> str:
    for limit, letter in ((90, "A"), (75, "B"), (60, "C"), (40, "D")):
        if score >= limit:
            return letter
    return "F"


def build_report(root: Path, skip: set[str]) -> dict:
    checks = [c for c in run_checks(root) if c.id not in skip]
    total = sum(c.max_points for c in checks)
    got = sum(c.points for c in checks)
    score = round(100 * got / total) if total else 100
    return {
        "path": str(root),
        "score": score,
        "grade": grade(score),
        "points": got,
        "max_points": total,
        "checks": [asdict(c) | {"passed": c.passed} for c in checks],
        "fixes": [
            {"id": c.id, "points_available": c.max_points - c.points, "fix": c.fix}
            for c in sorted(checks, key=lambda c: c.points - c.max_points)
            if not c.passed
        ],
    }


def format_text(report: dict) -> str:
    lines = [f"Repository health: {report['score']}/100 (grade {report['grade']})  {report['path']}", ""]
    for c in report["checks"]:
        mark = "PASS" if c["passed"] else ("PART" if c["points"] else "FAIL")
        lines.append(f"  [{mark}] {c['title']:<58} {c['points']:>2}/{c['max_points']}")
    if report["fixes"]:
        lines += ["", "Fixes, biggest gain first:"]
        for i, f in enumerate(report["fixes"], 1):
            lines.append(f"  {i}. (+{f['points_available']}) {f['fix']}")
    else:
        lines += ["", "Nothing to fix. Nice work."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score a local repository's open-source health (README, LICENSE, community files, CI, tests) and print fixes.",
    )
    parser.add_argument("path", nargs="?", default=".", help="repository root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    parser.add_argument("--min-score", type=int, default=0, help="exit 1 when the score is below this value (for CI)")
    parser.add_argument("--skip", default="", help="comma-separated check ids to skip, e.g. badges,changelog")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}
    report = build_report(root, skip)
    print(json.dumps(report, indent=2) if args.json else format_text(report))
    return 1 if report["score"] < args.min_score else 0


if __name__ == "__main__":
    sys.exit(main())
