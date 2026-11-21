#!/usr/bin/env python3
"""Generate, validate and apply a consistent GitHub label set.

  labels.py generate [--preset ...] [--area NAME ...] [--prefixed] > labels.json
  labels.py validate labels.json
  labels.py commands labels.json --repo OWNER/NAME > apply-labels.sh

`commands` only prints `gh label create ... --force` lines; nothing is sent to
GitHub until you review and run that script yourself.

Exit codes: 0 = ok, 1 = validation findings, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

MAX_NAME = 50
MAX_DESCRIPTION = 100

# name, prefixed name, color, description
PRESETS: dict[str, list[tuple[str, str, str, str]]] = {
    "type": [
        ("bug", "type: bug", "d73a4a", "Something is not working as documented"),
        ("enhancement", "type: enhancement", "a2eeef", "New feature or improvement to an existing one"),
        ("documentation", "type: documentation", "0075ca", "Improvements or additions to the docs"),
        ("question", "type: question", "d876e3", "Usage question; may move to Discussions"),
        ("performance", "type: performance", "fbca04", "Speed, memory or size improvements"),
        ("refactor", "type: refactor", "c5def5", "Internal change with no user-visible effect"),
    ],
    "contributor": [
        ("good first issue", "good first issue", "7057ff", "Small, well-described task for a first contribution"),
        ("help wanted", "help wanted", "008672", "Maintainers would welcome a pull request"),
    ],
    "status": [
        ("needs-triage", "status: needs triage", "ededed", "New issue a maintainer has not looked at yet"),
        ("needs-repro", "status: needs repro", "fef2c0", "Waiting for a minimal reproduction"),
        ("needs-info", "status: needs info", "fef2c0", "Waiting for more information from the reporter"),
        ("confirmed", "status: confirmed", "0e8a16", "Reproduced by a maintainer"),
        ("in-progress", "status: in progress", "1d76db", "Someone is working on this"),
        ("blocked", "status: blocked", "b60205", "Blocked by another issue or an upstream change"),
        ("stale", "status: stale", "cccccc", "No activity for a long time; closes soon unless updated"),
    ],
    "priority": [
        ("priority: critical", "priority: critical", "b60205", "Security, data loss or a broken release; fix now"),
        ("priority: high", "priority: high", "d93f0b", "Important; plan for the next release"),
        ("priority: low", "priority: low", "c2e0c6", "Nice to have"),
    ],
    "resolution": [
        ("duplicate", "resolution: duplicate", "cfd3d7", "This issue or pull request already exists"),
        ("invalid", "resolution: invalid", "e4e669", "Not a bug, or not actionable"),
        ("wontfix", "resolution: wontfix", "ffffff", "Out of scope for this project"),
    ],
    "dependencies": [
        ("dependencies", "dependencies", "0366d6", "Updates a dependency (used by Dependabot)"),
        ("security", "security", "b60205", "Security fix or hardening"),
        ("breaking-change", "breaking change", "e11d21", "Requires a major version bump"),
    ],
}
DEFAULT_PRESETS = ["type", "contributor", "status", "priority", "resolution", "dependencies"]
AREA_COLOR = "bfdadc"


def generate(presets: list[str], areas: list[str], prefixed: bool) -> list[dict]:
    labels: list[dict] = []
    for preset in presets:
        for plain, pref, color, desc in PRESETS[preset]:
            labels.append({"name": pref if prefixed else plain, "color": color, "description": desc})
    for area in areas:
        slug = area.strip().lower()
        if slug:
            labels.append({"name": f"area: {slug}", "color": AREA_COLOR, "description": f"Affects the {slug} area"})
    return labels


def validate(labels: object) -> list[str]:
    problems: list[str] = []
    if not isinstance(labels, list):
        return ["top level must be a JSON array of {name, color, description} objects"]
    seen: dict[str, int] = {}
    for i, label in enumerate(labels):
        where = f"[{i}]"
        if not isinstance(label, dict):
            problems.append(f"{where}: must be an object")
            continue
        name = label.get("name")
        if not isinstance(name, str) or not name.strip():
            problems.append(f"{where}: missing name")
            continue
        where = f"[{i}] {name!r}"
        if len(name) > MAX_NAME:
            problems.append(f"{where}: name longer than {MAX_NAME} characters")
        if name != name.strip():
            problems.append(f"{where}: leading or trailing whitespace")
        key = name.strip().lower()
        if key in seen:
            problems.append(f"{where}: duplicate of [{seen[key]}] (GitHub label names are case-insensitive)")
        seen.setdefault(key, i)
        color = label.get("color")
        if not isinstance(color, str) or not re.fullmatch(r"[0-9a-fA-F]{6}", color):
            problems.append(f"{where}: color must be 6 hex digits without '#', got {color!r}")
        desc = label.get("description", "")
        if not isinstance(desc, str):
            problems.append(f"{where}: description must be a string")
        elif len(desc) > MAX_DESCRIPTION:
            problems.append(f"{where}: description longer than {MAX_DESCRIPTION} characters")
    return problems


def commands(labels: list[dict], repo: str | None) -> str:
    lines = [
        "#!/bin/sh",
        "# Review, then run: sh apply-labels.sh   (requires the GitHub CLI, logged in with repo access)",
        "# --force updates the color and description of labels that already exist.",
        "set -e",
    ]
    repo_arg = f" --repo {shlex.quote(repo)}" if repo else ""
    for label in labels:
        cmd = f"gh label create {shlex.quote(label['name'])} --color {label['color']}"
        if label.get("description"):
            cmd += f" --description {shlex.quote(label['description'])}"
        lines.append(cmd + repo_arg + " --force")
    return "\n".join(lines) + "\n"


def load(path: str) -> object:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate, validate and apply a GitHub label set.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="print a labels JSON array")
    g.add_argument(
        "--preset",
        action="append",
        choices=sorted(PRESETS),
        help=f"label groups (default: {', '.join(DEFAULT_PRESETS)})",
    )
    g.add_argument("--area", action="append", default=[], help="add an 'area: NAME' label (repeatable)")
    g.add_argument("--prefixed", action="store_true", help="use 'type: bug' / 'status: ...' style names")

    v = sub.add_parser("validate", help="check a labels JSON file")
    v.add_argument("file", help="labels JSON file, or - for stdin")
    v.add_argument("--json", action="store_true", help="print problems as JSON")

    c = sub.add_parser("commands", help="print gh label create commands (dry run; nothing is executed)")
    c.add_argument("file", help="labels JSON file, or - for stdin")
    c.add_argument("--repo", help="OWNER/NAME; omit to target the repository of the current directory")

    args = parser.parse_args(argv)

    if args.cmd == "generate":
        labels = generate(args.preset or DEFAULT_PRESETS, args.area, args.prefixed)
        print(json.dumps(labels, indent=2))
        return 0

    try:
        data = load(args.file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    problems = validate(data)

    if args.cmd == "validate":
        if args.json:
            print(json.dumps({"ok": not problems, "problems": problems}, indent=2))
        else:
            for p in problems:
                print(p)
            print("ok" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    if problems:
        for p in problems:
            print(p, file=sys.stderr)
        return 1
    if args.repo and not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
        print("error: --repo must look like OWNER/NAME", file=sys.stderr)
        return 2
    sys.stdout.write(commands(data, args.repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
