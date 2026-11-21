#!/usr/bin/env python3
"""Validate every skill in this repository and the Claude Code plugin manifests.

Checks per skill (skills/<name>/SKILL.md):
  - YAML frontmatter present; only Agent Skills spec keys
  - name: 1-64 chars, lowercase letters/digits/single hyphens, equals the folder name
  - description: 1-1024 chars and says when to use the skill ("Use when ...")
  - compatibility (if present): at most 500 chars; metadata: a map of strings
  - required sections: When to use, When not to use, Workflow, Output
  - body at most 400 lines (move long material to references/)
  - every relative link and every scripts/, references/, assets/ path mentioned exists
  - every script under scripts/ has a test file tests/test_<script>.py and answers --help

Checks for the repository:
  - .claude-plugin/plugin.json and .claude-plugin/marketplace.json are valid JSON with
    the required fields, names agree, and the marketplace lists exactly the skills on disk
  - templates/skill/SKILL.md keeps the required sections

Exit codes: 0 = valid, 1 = problems found, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REQUIRED_SECTIONS = ("When to use", "When not to use", "Workflow", "Output")
MAX_BODY_LINES = 400
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500
PATH_MENTION = re.compile(r"(?<![\w./-])((?:scripts|references|assets)/[\w./-]+\w)")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


class FrontmatterError(ValueError):
    pass


def _scalar(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        inner = raw[1:-1]
        return inner.replace('\\"', '"') if raw[0] == '"' else inner.replace("''", "'")
    if raw.startswith(("[", "{", "|", ">", "&", "*", "!")):
        raise FrontmatterError(f"unsupported YAML value {raw[:20]!r}; use a plain or quoted string")
    if " #" in raw:
        raw = raw.split(" #", 1)[0].rstrip()
    if ": " in raw or raw.endswith(":"):
        raise FrontmatterError(f"value {raw[:30]!r}... contains ': '; wrap it in quotes so YAML parsers accept it")
    return raw


def parse_frontmatter(text: str) -> tuple[dict, str, int]:
    """Parse the simple YAML subset used by SKILL.md frontmatter.

    Supports `key: value` pairs (plain or quoted strings) and one level of nested
    `key:` maps indented by spaces. Returns (data, body, body_start_line).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("SKILL.md must start with '---' frontmatter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter is not closed with '---'") from None
    data: dict = {}
    current: str | None = None
    for no, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            if current is None or not isinstance(data.get(current), dict):
                raise FrontmatterError(f"line {no}: unexpected indentation")
            m = re.match(r"^\s+([\w.-]+):\s*(.*)$", line)
            if not m or not m.group(2).strip():
                raise FrontmatterError(f"line {no}: nested entries must be 'key: value'")
            data[current][m.group(1)] = _scalar(m.group(2))
            continue
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if not m:
            raise FrontmatterError(f"line {no}: expected 'key: value'")
        key, value = m.group(1), m.group(2)
        if key in data:
            raise FrontmatterError(f"line {no}: duplicate key {key!r}")
        if value.strip():
            data[key] = _scalar(value)
            current = None
        else:
            data[key] = {}
            current = key
    body = "\n".join(lines[end + 1 :])
    return data, body, end + 2


def strip_code_blocks(body: str) -> str:
    out, fence = [], None
    for line in body.splitlines():
        s = line.lstrip()
        if fence is None and s[:3] in ("```", "~~~"):
            fence = s[:3]
            out.append("")
            continue
        if fence is not None:
            if s.startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def validate_skill(skill_dir: Path, repo: Path, run_help: bool = True) -> list[str]:
    errors: list[str] = []
    rel = skill_dir.relative_to(repo).as_posix()
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{rel}: missing SKILL.md"]
    text = md.read_text(encoding="utf-8")
    try:
        meta, body, _ = parse_frontmatter(text)
    except FrontmatterError as exc:
        return [f"{rel}/SKILL.md: {exc}"]

    unknown = set(meta) - ALLOWED_KEYS
    if unknown:
        errors.append(f"{rel}: unknown frontmatter keys {sorted(unknown)} (allowed: {sorted(ALLOWED_KEYS)})")

    name = meta.get("name")
    if not isinstance(name, str) or not name:
        errors.append(f"{rel}: 'name' is required")
    else:
        if len(name) > MAX_NAME:
            errors.append(f"{rel}: name is {len(name)} chars (max {MAX_NAME})")
        if not NAME_RE.match(name):
            errors.append(f"{rel}: name {name!r} must be lowercase letters, digits and single hyphens")
        if name != skill_dir.name:
            errors.append(f"{rel}: name {name!r} must match the folder name {skill_dir.name!r}")

    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append(f"{rel}: 'description' is required")
    else:
        if len(desc) > MAX_DESCRIPTION:
            errors.append(f"{rel}: description is {len(desc)} chars (max {MAX_DESCRIPTION})")
        if "use when" not in desc.lower():
            errors.append(f"{rel}: description must say when to use the skill ('Use when ...')")

    compat = meta.get("compatibility")
    if compat is not None and (not isinstance(compat, str) or not 1 <= len(compat) <= MAX_COMPATIBILITY):
        errors.append(f"{rel}: compatibility must be 1-{MAX_COMPATIBILITY} characters")
    md_meta = meta.get("metadata")
    if md_meta is not None and not (isinstance(md_meta, dict) and all(isinstance(v, str) for v in md_meta.values())):
        errors.append(f"{rel}: metadata must be a map of string values")

    prose = strip_code_blocks(body)
    headings = [h.strip().lower() for h in re.findall(r"^##\s+(.+)$", prose, re.M)]
    for section in REQUIRED_SECTIONS:
        if section.lower() not in headings:
            errors.append(f"{rel}: missing required section '## {section}'")

    n_lines = len(body.splitlines())
    if n_lines > MAX_BODY_LINES:
        errors.append(f"{rel}: SKILL.md body is {n_lines} lines (max {MAX_BODY_LINES}); move detail to references/")

    mentioned: set[str] = set()
    for target in LINK_RE.findall(prose):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.I):
            continue
        mentioned.add(target.split("#", 1)[0])
    mentioned.update(PATH_MENTION.findall(body))
    for target in sorted(t for t in mentioned if t):
        if not (skill_dir / target).exists():
            errors.append(f"{rel}: references '{target}' which does not exist")

    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        for script in sorted(scripts.iterdir()):
            if script.suffix not in {".py", ".sh"} or script.name.startswith("_"):
                continue
            test = repo / "tests" / f"test_{script.stem}.py"
            if not test.is_file():
                errors.append(f"{rel}: script {script.name} has no test file tests/{test.name}")
            if run_help:
                cmd = (
                    [sys.executable, str(script), "--help"] if script.suffix == ".py" else ["sh", str(script), "--help"]
                )
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    ok = proc.returncode == 0 and proc.stdout.strip()
                except (OSError, subprocess.TimeoutExpired):
                    ok = False
                if not ok:
                    errors.append(f"{rel}: '{script.name} --help' must exit 0 and print usage")
    return errors


def load_json(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"{path.name}: missing ({path})")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name}: invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path.name}: top level must be an object")
        return None
    return data


def validate_manifests(repo: Path, skill_names: list[str]) -> list[str]:
    errors: list[str] = []
    plugin = load_json(repo / ".claude-plugin" / "plugin.json", errors)
    market = load_json(repo / ".claude-plugin" / "marketplace.json", errors)
    if plugin is not None:
        if not isinstance(plugin.get("name"), str) or not NAME_RE.match(plugin.get("name", "")):
            errors.append("plugin.json: 'name' is required and must be kebab-case")
        if not isinstance(plugin.get("version"), str):
            errors.append("plugin.json: 'version' should be set")
    if market is None:
        return errors
    if not isinstance(market.get("name"), str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]*", market.get("name", "")
    ):
        errors.append("marketplace.json: 'name' is required (letters, digits, '.', '_', '-')")
    owner = market.get("owner")
    if not isinstance(owner, dict) or not owner.get("name"):
        errors.append("marketplace.json: 'owner.name' is required")
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        errors.append("marketplace.json: 'plugins' must be a non-empty array")
        return errors
    listed: list[str] = []
    for i, entry in enumerate(plugins):
        if not isinstance(entry, dict) or not entry.get("name") or "source" not in entry:
            errors.append(f"marketplace.json: plugins[{i}] needs 'name' and 'source'")
            continue
        source = entry["source"]
        if isinstance(source, str):
            if not (source == "." or source.startswith("./")) or ".." in source:
                errors.append(f"marketplace.json: plugins[{i}].source must start with './' and not contain '..'")
            elif not (repo / source).is_dir():
                errors.append(f"marketplace.json: plugins[{i}].source {source!r} does not exist")
            base = repo / source
            if plugin is not None and base.resolve() == repo.resolve() and entry["name"] != plugin.get("name"):
                errors.append(
                    f"marketplace.json: plugins[{i}].name {entry['name']!r} differs from plugin.json name {plugin.get('name')!r}"
                )
        else:
            base = None
        for path in entry.get("skills", []) or []:
            if not isinstance(path, str) or not path.startswith("./") or ".." in path:
                errors.append(f"marketplace.json: plugins[{i}].skills entry {path!r} must start with './'")
                continue
            target = (base or repo) / path
            if not (target / "SKILL.md").is_file():
                errors.append(f"marketplace.json: plugins[{i}].skills entry {path!r} has no SKILL.md")
            listed.append(Path(path).name)
    missing = sorted(set(skill_names) - set(listed))
    extra = sorted(set(listed) - set(skill_names))
    if missing:
        errors.append(f"marketplace.json: skills not listed in any plugin entry: {missing}")
    if extra:
        errors.append(f"marketplace.json: listed skills not found under skills/: {extra}")
    if len(listed) != len(set(listed)):
        errors.append("marketplace.json: a skill is listed more than once")
    return errors


def validate_template(repo: Path) -> list[str]:
    tpl = repo / "templates" / "skill" / "SKILL.md"
    if not tpl.is_file():
        return ["templates/skill/SKILL.md: missing"]
    try:
        meta, body, _ = parse_frontmatter(tpl.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        return [f"templates/skill/SKILL.md: {exc}"]
    headings = [h.strip().lower() for h in re.findall(r"^##\s+(.+)$", strip_code_blocks(body), re.M)]
    errors = [
        f"templates/skill/SKILL.md: missing section '## {s}'" for s in REQUIRED_SECTIONS if s.lower() not in headings
    ]
    if not {"name", "description"} <= set(meta):
        errors.append("templates/skill/SKILL.md: frontmatter needs name and description")
    return errors


def validate_repo(repo: Path, run_help: bool = True) -> dict:
    skills_dir = repo / "skills"
    if not skills_dir.is_dir():
        return {"ok": False, "skills": [], "errors": ["skills/ directory not found"]}
    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("."))
    errors: list[str] = []
    for d in skill_dirs:
        errors.extend(validate_skill(d, repo, run_help))
    errors.extend(validate_manifests(repo, [d.name for d in skill_dirs]))
    errors.extend(validate_template(repo))
    return {"ok": not errors, "skills": [d.name for d in skill_dirs], "errors": errors}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SKILL.md files and the Claude Code plugin manifests.")
    parser.add_argument("repo", nargs="?", default=str(Path(__file__).resolve().parent.parent), help="repository root")
    parser.add_argument("--json", action="store_true", help="print a JSON result")
    parser.add_argument("--no-exec", action="store_true", help="do not run scripts with --help")
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"error: {repo} is not a directory", file=sys.stderr)
        return 2
    result = validate_repo(repo, not args.no_exec)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for e in result["errors"]:
            print(f"ERROR {e}")
        status = "ok" if result["ok"] else f"{len(result['errors'])} problem(s)"
        print(f"{len(result['skills'])} skill(s) checked: {status}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
