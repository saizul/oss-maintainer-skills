#!/usr/bin/env python3
"""Pre-release checks: version consistency, changelog entry, git state, tag availability.

  release_preflight.py [PATH] [--version 1.4.0] [--no-git] [--json]

Version sources checked when present: pyproject.toml ([project] or [tool.poetry]),
package.json, composer.json ("version" is optional there), Cargo.toml, and any
--version-file containing __version__ = "...". Git checks only read state
(status, tags, branch); nothing is committed, tagged or pushed.

Exit codes: 0 = ready (warnings allowed), 1 = at least one check failed, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
DUNDER = re.compile(r"""^__version__\s*=\s*["']([^"']+)["']""", re.M)


def manifest_versions(root: Path, extra_files: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    py = root / "pyproject.toml"
    if py.is_file():
        try:
            data = tomllib.loads(py.read_text(encoding="utf-8"))
            project = data.get("project") or {}
            poetry = (data.get("tool") or {}).get("poetry") or {}
            if "version" in project:
                found["pyproject.toml"] = str(project["version"])
            elif "version" in poetry:
                found["pyproject.toml"] = str(poetry["version"])
        except tomllib.TOMLDecodeError:
            found["pyproject.toml"] = "<invalid TOML>"
    for name in ("package.json", "composer.json"):
        p = root / name
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "version" in data:
                    found[name] = str(data["version"])
            except json.JSONDecodeError:
                found[name] = "<invalid JSON>"
    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            pkg = tomllib.loads(cargo.read_text(encoding="utf-8")).get("package") or {}
            if isinstance(pkg.get("version"), str):
                found["Cargo.toml"] = pkg["version"]
        except tomllib.TOMLDecodeError:
            found["Cargo.toml"] = "<invalid TOML>"
    for rel in extra_files:
        p = root / rel
        if p.is_file():
            m = DUNDER.search(p.read_text(encoding="utf-8"))
            found[rel] = m.group(1) if m else "<no __version__>"
        else:
            found[rel] = "<missing file>"
    return found


def changelog_check(root: Path, version: str) -> tuple[str, str]:
    path = next(
        (root / n for n in ("CHANGELOG.md", "CHANGELOG", "CHANGES.md", "HISTORY.md") if (root / n).is_file()), None
    )
    if path is None:
        return "fail", "No CHANGELOG.md. Add one with a section for this version."
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"^#{1,3}\s*\[?v?" + re.escape(version) + r"\]?(\s|$)", re.M)
    m = pattern.search(text)
    if not m:
        if re.search(r"^#{1,3}\s*\[?unreleased\]?", text, re.I | re.M):
            return (
                "fail",
                f"{path.name} has an Unreleased section but no '{version}' heading; rename it to '## [{version}] - YYYY-MM-DD'.",
            )
        return "fail", f"{path.name} has no heading for {version}."
    line_end = text.find("\n", m.start())
    start = len(text) if line_end == -1 else line_end + 1
    nxt = re.search(r"^#{1,2}\s", text[start:], re.M)
    body = text[start : start + nxt.start()] if nxt else text[start:]
    if not re.search(r"^\s*[-*]\s+\S", body, re.M):
        return "fail", f"The {version} section in {path.name} has no entries."
    return "pass", f"{path.name} has a {version} section."


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def git_checks(root: Path, version: str, tag_prefix: str, branches: list[str]) -> list[dict]:
    out = []
    if git(root, "rev-parse", "--is-inside-work-tree").returncode != 0:
        return [{"id": "git", "status": "warn", "message": "Not a git repository; git checks skipped."}]
    status = git(root, "status", "--porcelain").stdout.strip()
    if status:
        n = len(status.splitlines())
        out.append(
            {
                "id": "clean-tree",
                "status": "fail",
                "message": f"{n} uncommitted change(s). Commit or stash before tagging.",
            }
        )
    else:
        out.append({"id": "clean-tree", "status": "pass", "message": "Working tree is clean."})
    tag = f"{tag_prefix}{version}"
    if git(root, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode == 0:
        out.append(
            {
                "id": "tag-free",
                "status": "fail",
                "message": f"Tag {tag} already exists. Bump the version or delete the stale tag.",
            }
        )
    else:
        out.append({"id": "tag-free", "status": "pass", "message": f"Tag {tag} is available."})
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch in branches:
        out.append({"id": "branch", "status": "pass", "message": f"On release branch '{branch}'."})
    else:
        out.append(
            {
                "id": "branch",
                "status": "warn",
                "message": f"On '{branch}', not {' or '.join(branches)}. Is that intended?",
            }
        )
    upstream = git(root, "rev-list", "--count", "--left-right", "@{upstream}...HEAD")
    if upstream.returncode == 0:
        behind, ahead = (int(x) for x in upstream.stdout.split())
        if behind:
            out.append(
                {
                    "id": "upstream",
                    "status": "fail",
                    "message": f"Branch is {behind} commit(s) behind its upstream. Pull first.",
                }
            )
        elif ahead:
            out.append(
                {
                    "id": "upstream",
                    "status": "warn",
                    "message": f"{ahead} local commit(s) not pushed yet. Push before tagging.",
                }
            )
        else:
            out.append({"id": "upstream", "status": "pass", "message": "Branch is in sync with its upstream."})
    return out


def run(root: Path, version: str | None, extra: list[str], use_git: bool, tag_prefix: str, branches: list[str]) -> dict:
    checks: list[dict] = []
    versions = manifest_versions(root, extra)
    if version is None:
        candidates = sorted(set(versions.values()))
        version = candidates[0] if len(candidates) == 1 else None
    if version is None:
        checks.append(
            {"id": "version", "status": "fail", "message": "Could not determine the version; pass --version X.Y.Z."}
        )
        return {"version": None, "ready": False, "checks": checks, "manifests": versions}
    version = version.lstrip("v")
    if SEMVER.match(version):
        checks.append({"id": "semver", "status": "pass", "message": f"{version} is a valid semantic version."})
    else:
        checks.append(
            {"id": "semver", "status": "fail", "message": f"{version!r} is not a valid semantic version (X.Y.Z)."}
        )
    if versions:
        wrong = {k: v for k, v in versions.items() if v != version}
        if wrong:
            detail = ", ".join(f"{k}={v}" for k, v in wrong.items())
            checks.append(
                {"id": "manifests", "status": "fail", "message": f"Version mismatch: {detail} (expected {version})."}
            )
        else:
            checks.append(
                {"id": "manifests", "status": "pass", "message": f"All manifests say {version}: {', '.join(versions)}."}
            )
    else:
        checks.append(
            {
                "id": "manifests",
                "status": "warn",
                "message": "No versioned manifest found; the tag will be the only version record.",
            }
        )
    status, message = changelog_check(root, version)
    checks.append({"id": "changelog", "status": status, "message": message})
    if not any((root / n).is_file() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")):
        checks.append(
            {"id": "license", "status": "fail", "message": "No LICENSE file; packages without one are not reusable."}
        )
    if use_git:
        checks.extend(git_checks(root, version, tag_prefix, branches))
    ready = not any(c["status"] == "fail" for c in checks)
    return {
        "version": version,
        "tag": f"{tag_prefix}{version}",
        "ready": ready,
        "checks": checks,
        "manifests": versions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that a repository is ready to tag a release.")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--version", help="version to release (default: the one all manifests agree on)")
    parser.add_argument(
        "--version-file", action="append", default=[], help="extra file with __version__ = '...' (repeatable)"
    )
    parser.add_argument("--tag-prefix", default="v", help="tag prefix (default: v)")
    parser.add_argument("--branch", action="append", help="allowed release branch (default: main, master)")
    parser.add_argument("--no-git", action="store_true", help="skip git checks")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    result = run(
        root, args.version, args.version_file, not args.no_git, args.tag_prefix, args.branch or ["main", "master"]
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Release preflight for {result.get('tag') or '(unknown version)'}")
        for c in result["checks"]:
            print(f"  [{c['status'].upper():<4}] {c['message']}")
        print("\nReady to tag." if result["ready"] else "\nNot ready: fix the FAIL items above.")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
