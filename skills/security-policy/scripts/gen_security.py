#!/usr/bin/env python3
"""Generate SECURITY.md and .github/dependabot.yml, and check that both are in place.

  gen_security.py ecosystems [PATH] [--json]
  gen_security.py dependabot [PATH] [--interval weekly] [--no-groups] [--write [--force]]
  gen_security.py security-md --repo OWNER/NAME [--project NAME] [--supported "1.x"] [--write [--force]]
  gen_security.py check [PATH] [--json]

Everything prints to stdout unless --write is given; --write never overwrites an
existing file without --force. No network access.

Exit codes: 0 = ok, 1 = check found problems or the target file exists, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", "vendor", ".venv", "venv", "dist", "build", "__pycache__", "target", ".tox"}

# ecosystem -> filename patterns (exact names, or glob suffixes starting with *)
MANIFESTS: dict[str, tuple[str, ...]] = {
    "pip": ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "Pipfile"),
    "npm": ("package.json",),
    "composer": ("composer.json",),
    "docker": ("Dockerfile", "*.Dockerfile"),
    "gomod": ("go.mod",),
    "cargo": ("Cargo.toml",),
    "bundler": ("Gemfile",),
    "maven": ("pom.xml",),
    "gradle": ("build.gradle", "build.gradle.kts"),
    "nuget": ("*.csproj", "*.fsproj", "packages.config"),
}
ORDER = ["github-actions", *MANIFESTS]


def matches(name: str, patterns: tuple[str, ...]) -> bool:
    return any(name.endswith(p[1:]) if p.startswith("*") else name == p for p in patterns)


def detect_ecosystems(root: Path, max_depth: int = 3) -> list[dict]:
    """Return [{ecosystem, directory}] like Dependabot expects ("/" = repo root)."""
    found: set[tuple[str, str]] = set()
    workflows = root / ".github" / "workflows"
    if workflows.is_dir() and any(p.suffix in {".yml", ".yaml"} for p in workflows.iterdir()):
        found.add(("github-actions", "/"))
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError:
            continue
        for p in entries:
            if p.is_dir():
                if p.name not in SKIP_DIRS and not p.name.startswith(".") and depth < max_depth:
                    stack.append((p, depth + 1))
                continue
            for eco, patterns in MANIFESTS.items():
                if matches(p.name, patterns):
                    rel = p.parent.relative_to(root).as_posix()
                    found.add((eco, "/" if rel == "." else "/" + rel))
    return [{"ecosystem": e, "directory": d} for e, d in sorted(found, key=lambda x: (ORDER.index(x[0]), x[1]))]


def dependabot_yaml(ecosystems: list[dict], interval: str, groups: bool, limit: int) -> str:
    lines = [
        "# Dependabot version updates. Docs:",
        "# https://docs.github.com/code-security/dependabot/working-with-dependabot/dependabot-options-reference",
        "version: 2",
        "updates:",
    ]
    for item in ecosystems:
        eco = item["ecosystem"]
        lines += [
            f"  - package-ecosystem: {eco}",
            f'    directory: "{item["directory"]}"',
            "    schedule:",
            f"      interval: {interval}",
            f"    open-pull-requests-limit: {limit}",
            "    labels:",
            "      - dependencies",
        ]
        if eco == "github-actions":
            lines += ["    commit-message:", "      prefix: ci"]
        else:
            lines += ["    commit-message:", "      prefix: deps", "      prefix-development: deps-dev"]
        if groups:
            lines += [
                "    groups:",
                f"      {eco}-minor-and-patch:",
                "        update-types:",
                "          - minor",
                "          - patch",
            ]
    return "\n".join(lines) + "\n"


def security_md(project: str, repo: str, supported: list[str], response_days: int, fix_days: int) -> str:
    rows = "\n".join(f"| {v} | :white_check_mark: |" for v in supported)
    return f"""# Security Policy

## Supported versions

Security fixes are released for these versions:

| Version | Supported |
| --- | --- |
{rows}
| Older | :x: |

## Reporting a vulnerability

**Please do not open a public issue, discussion or pull request for security problems.**

Report it privately through
[GitHub private vulnerability reporting](https://github.com/{repo}/security/advisories/new)
(Security tab, then "Report a vulnerability"). Include:

- the affected version of {project} and your environment;
- what an attacker can do (impact) and what they need (preconditions);
- steps or a minimal proof of concept to reproduce it;
- any suggested fix or mitigation.

Do not include real credentials, tokens or personal data in the report.

## What to expect

- An acknowledgement within **{response_days} working days**.
- An assessment (accepted or declined, with reasons) within **{response_days * 2} working days**.
- For accepted reports, a fix or mitigation target of **{fix_days} days**, depending on complexity.
  We will keep you updated and agree on a disclosure date with you.
- Credit in the release notes and the published advisory, unless you prefer to stay anonymous.

## Scope

In scope: the code in this repository and the packages released from it.
Out of scope: vulnerabilities in dependencies that are already public (please report those
upstream), social engineering, and issues that need a compromised machine or account.
"""


def check(root: Path) -> dict:
    problems: list[str] = []
    notes: list[str] = []
    sec = next(
        (root / d / "SECURITY.md" for d in ("", ".github", "docs") if (root / d / "SECURITY.md").is_file()), None
    )
    if sec is None:
        problems.append(
            "No SECURITY.md in the root, .github/ or docs/. Run: gen_security.py security-md --repo OWNER/NAME --write"
        )
    else:
        text = sec.read_text(encoding="utf-8", errors="replace")
        if not re.search(
            r"(security/advisories/new|report a vulnerability|private vulnerability|@|mailto:)", text, re.I
        ):
            problems.append(
                f"{sec.relative_to(root)} does not name a private reporting channel (advisory link or address)."
            )
        if not re.search(r"supported versions", text, re.I):
            notes.append(f"{sec.relative_to(root)} has no 'Supported versions' section.")
    dep = next(
        (p for p in (root / ".github" / "dependabot.yml", root / ".github" / "dependabot.yaml") if p.is_file()), None
    )
    detected = detect_ecosystems(root)
    if dep is None:
        renovate = any(
            (root / n).exists() for n in ("renovate.json", "renovate.json5", ".renovaterc", ".github/renovate.json")
        )
        if renovate:
            notes.append("Renovate config found; skipping the Dependabot coverage check.")
        else:
            problems.append("No .github/dependabot.yml. Run: gen_security.py dependabot --write")
    else:
        text = dep.read_text(encoding="utf-8", errors="replace")
        covered = set(re.findall(r"package-ecosystem:\s*[\"']?([\w-]+)", text))
        for eco in sorted({d["ecosystem"] for d in detected} - covered, key=ORDER.index):
            problems.append(f"dependabot.yml does not cover the '{eco}' ecosystem found in this repository.")
    notes.append(
        "Also enable in Settings > Security: private vulnerability reporting, Dependabot alerts and security updates, secret scanning."
    )
    return {"ok": not problems, "problems": problems, "notes": notes, "ecosystems": detected}


def write_or_print(content: str, target: Path, write: bool, force: bool) -> int:
    if not write:
        sys.stdout.write(content)
        return 0
    if target.exists() and not force:
        print(f"error: {target} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"wrote {target}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate SECURITY.md and dependabot.yml, and check both.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("ecosystems", help="list package ecosystems Dependabot can update")
    e.add_argument("path", nargs="?", default=".")
    e.add_argument("--json", action="store_true")

    d = sub.add_parser("dependabot", help="generate .github/dependabot.yml")
    d.add_argument("path", nargs="?", default=".")
    d.add_argument("--interval", choices=["daily", "weekly", "monthly"], default="weekly")
    d.add_argument("--limit", type=int, default=5, help="open-pull-requests-limit per ecosystem (default 5)")
    d.add_argument("--no-groups", action="store_true", help="one PR per dependency instead of grouped minor/patch PRs")
    d.add_argument("--write", action="store_true", help="write PATH/.github/dependabot.yml")
    d.add_argument("--force", action="store_true")

    s = sub.add_parser("security-md", help="generate SECURITY.md")
    s.add_argument("path", nargs="?", default=".")
    s.add_argument("--repo", required=True, help="OWNER/NAME on GitHub")
    s.add_argument("--project", help="project name (default: NAME from --repo)")
    s.add_argument("--supported", action="append", help="supported version line, repeatable (default: latest)")
    s.add_argument("--response-days", type=int, default=5)
    s.add_argument("--fix-days", type=int, default=90)
    s.add_argument("--write", action="store_true", help="write PATH/SECURITY.md")
    s.add_argument("--force", action="store_true")

    c = sub.add_parser("check", help="verify SECURITY.md and Dependabot coverage")
    c.add_argument("path", nargs="?", default=".")
    c.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = Path(args.path)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2

    if args.cmd == "ecosystems":
        eco = detect_ecosystems(root)
        if args.json:
            print(json.dumps(eco, indent=2))
        else:
            for item in eco:
                print(f"{item['ecosystem']:<15} {item['directory']}")
        return 0

    if args.cmd == "dependabot":
        eco = detect_ecosystems(root)
        if not eco:
            print("error: no supported manifests or workflows found", file=sys.stderr)
            return 1
        content = dependabot_yaml(eco, args.interval, not args.no_groups, args.limit)
        return write_or_print(content, root / ".github" / "dependabot.yml", args.write, args.force)

    if args.cmd == "security-md":
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", args.repo):
            print("error: --repo must look like OWNER/NAME", file=sys.stderr)
            return 2
        project = args.project or args.repo.split("/", 1)[1]
        content = security_md(
            project, args.repo, args.supported or ["latest release"], args.response_days, args.fix_days
        )
        return write_or_print(content, root / "SECURITY.md", args.write, args.force)

    result = check(root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for p in result["problems"]:
            print(f"FAIL  {p}")
        for n in result["notes"]:
            print(f"note  {n}")
        print("ok" if result["ok"] else f"{len(result['problems'])} problem(s)")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
