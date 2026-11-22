#!/usr/bin/env python3
"""Lint a README for the things that turn visitors into users and contributors.

Checks the title, one-line pitch, badges, install and quick-start sections,
code examples, how far a reader scrolls before the first command, relative
links, in-page #anchor links (table of contents), image alt text, and the
contributing and license sections.

Read-only. Exit codes: 0 = no errors (and no warnings with --strict),
1 = findings at the failing level, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    line: int | None = None


@dataclass
class Section:
    level: int
    title: str
    line: int


def strip_code(lines: list[str]) -> list[tuple[int, str, bool]]:
    """Return (line_no, text, in_code) for every line."""
    out = []
    fence: str | None = None
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if fence is None and marker in ("```", "~~~"):
            fence = marker
            out.append((i, line, True))
            continue
        if fence is not None:
            out.append((i, line, True))
            if stripped.startswith(fence):
                fence = None
            continue
        out.append((i, line, False))
    return out


def parse_sections(rows: list[tuple[int, str, bool]]) -> list[Section]:
    sections = []
    for i, line, in_code in rows:
        if in_code:
            continue
        m = re.match(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            sections.append(Section(len(m.group(1)), m.group(2), i))
    return sections


def find_sections(sections: list[Section], *words: str) -> list[Section]:
    return [s for s in sections if any(w in s.title.lower() for w in words)]


def find_section(sections: list[Section], *words: str) -> Section | None:
    found = find_sections(sections, *words)
    return found[0] if found else None


def section_has_code(rows: list[tuple[int, str, bool]], sections: list[Section], target: Section) -> bool:
    later = [s.line for s in sections if s.line > target.line and s.level <= target.level]
    end = min(later) if later else 10**9
    return any(in_code for i, _, in_code in rows if target.line < i < end)


BADGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*(shields\.io|badge|/workflows/|codecov|badgen)[^)]*\)")
TOC_LINE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\[[^\]]+\]\(#")
HTML_ANCHOR = re.compile(r"<a\s[^>]*(?:name|id)\s*=\s*[\"']([^\"']+)[\"']|\sid\s*=\s*[\"']([^\"']+)[\"']", re.I)


def heading_slug(title: str) -> str:
    """GitHub's heading anchor: lowercase, markup and punctuation removed, spaces to '-'."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", title)  # links and images -> label
    text = re.sub(r"<[^>]+>", "", text)  # inline HTML
    text = text.replace("`", "").lower()
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return text.replace(" ", "-")


def anchors(sections: list[Section], rows: list[tuple[int, str, bool]]) -> set[str]:
    """Every in-page anchor: heading slugs (with GitHub's -1, -2 suffixes) and HTML ids."""
    found: set[str] = set()
    counts: dict[str, int] = {}
    for section in sections:
        slug = heading_slug(section.title)
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        found.add(slug if n == 0 else f"{slug}-{n}")
    for _, line, in_code in rows:
        if not in_code:
            for m in HTML_ANCHOR.finditer(line):
                found.add((m.group(1) or m.group(2)).lower())
    return found


LINK_RE = re.compile(r"(!?)\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def pitch_paragraph(rows: list[tuple[int, str, bool]], sections: list[Section]) -> tuple[str, int | None]:
    """First prose paragraph after the H1 (badges and images ignored)."""
    start = sections[0].line if sections and sections[0].level == 1 else 0
    buf: list[str] = []
    first_line = None
    for i, line, in_code in rows:
        if i <= start:
            continue
        if in_code:
            if buf:
                break
            continue
        text = line.strip()
        if re.match(r"^#{1,6}\s", text):
            break
        if not text:
            if buf:
                break
            continue
        cleaned = re.sub(r"\[?!\[[^\]]*\]\([^)]*\)\]?(\([^)]*\))?", "", text).strip()
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        cleaned = re.sub(r"\*\*|__|`", "", cleaned).strip()
        if not cleaned:
            continue
        if first_line is None:
            first_line = i
        buf.append(cleaned)
    return " ".join(buf), first_line


def lint(text: str, base_dir: Path | None = None, max_scroll: int = 60) -> list[Finding]:
    lines = text.splitlines()
    rows = strip_code(lines)
    sections = parse_sections(rows)
    findings: list[Finding] = []

    def add(rule, severity, message, line=None):
        findings.append(Finding(rule, severity, message, line))

    if not text.strip():
        add("empty", "error", "README is empty.")
        return findings

    h1 = [s for s in sections if s.level == 1]
    if not h1:
        add("title", "error", "Add a single H1 title with the project name ('# project-name').")
    elif len(h1) > 1:
        add("title", "warning", f"Found {len(h1)} H1 headings; keep one H1 and use '##' for sections.", h1[1].line)

    pitch, pitch_line = pitch_paragraph(rows, sections)
    if not pitch:
        add(
            "pitch",
            "error",
            "Add a one-sentence pitch right under the title: what it is, who it is for, why it is better.",
        )
    else:
        first_sentence = re.split(r"(?<=[.!?])\s", pitch, maxsplit=1)[0]
        if len(first_sentence) > 200:
            add(
                "pitch",
                "warning",
                f"The first sentence is {len(first_sentence)} characters; cut the pitch to under 200.",
                pitch_line,
            )
        if len(first_sentence.split()) < 4:
            add("pitch", "warning", "The pitch is very short; say what the project does and for whom.", pitch_line)

    if not BADGE_RE.search(text):
        add("badges", "warning", "Add badges under the title: CI status, latest version and license.")

    installs = find_sections(sections, "install", "getting started", "setup", "quick start", "quickstart")
    if not installs:
        add("install", "error", "Add an '## Installation' section with the exact command (pip/npm/composer/brew...).")
    elif not any(section_has_code(rows, sections, s) for s in installs):
        add("install", "warning", "The install section has no code block; show the exact command.", installs[0].line)

    quicks = find_sections(sections, "quick start", "quickstart", "usage", "example", "getting started", "how to use")
    if not quicks:
        add(
            "quickstart",
            "error",
            "Add a '## Quick start' or '## Usage' section with a runnable example and its output.",
        )
    elif not any(section_has_code(rows, sections, s) for s in quicks):
        add("quickstart", "warning", "The usage section has no code example.", quicks[0].line)

    first_code = next((i for i, _, in_code in rows if in_code), None)
    if first_code is None:
        add("code", "error", "The README has no fenced code block; readers copy commands, give them one.")
    elif first_code > max_scroll:
        add(
            "scroll",
            "warning",
            f"The first code block is on line {first_code}; move a quick start above line {max_scroll}.",
            first_code,
        )

    if find_section(sections, "contribut") is None:
        add(
            "contributing",
            "warning",
            "Add a '## Contributing' section that links CONTRIBUTING.md and good first issues.",
        )
    if find_section(sections, "license", "licence") is None:
        add("license", "warning", "Add a '## License' section naming the license and linking LICENSE.")
    if find_section(sections, "faq", "questions", "troubleshoot") is None:
        add("faq", "info", "Consider a short FAQ: answer 'why not X?', platform support and common errors.")
    anchor_lines = sum(1 for _, line, c in rows if not c and TOC_LINE.match(line))
    has_toc = find_section(sections, "contents", "table of contents") is not None or anchor_lines >= 4
    if len([s for s in sections if s.level == 2]) >= 8 and not has_toc:
        add("toc", "info", "The README has many sections; add a table of contents near the top.")

    known_anchors = anchors(sections, rows)
    for i, line, in_code in rows:
        if in_code:
            continue
        for m in LINK_RE.finditer(line):
            is_image, label, target = m.group(1) == "!", m.group(2), m.group(3)
            if is_image and not label.strip():
                add("alt-text", "warning", f"Image '{target}' has no alt text.", i)
            if target.startswith("#") and len(target) > 1:
                fragment = unquote(target[1:]).lower()
                if fragment not in known_anchors:
                    add("broken-anchor", "error", f"Link '{target}' does not match any heading in the README.", i)
            if base_dir is not None and not re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", target, re.I):
                rel = unquote(target.split("#", 1)[0].split("?", 1)[0])
                if rel and not (base_dir / rel).exists():
                    add("broken-link", "error", f"Relative link '{target}' points to a file that does not exist.", i)
        if re.search(r"\]\(\s*\)", line):
            add("broken-link", "error", "Empty link target '()'.", i)

    if re.search(r"\b(TODO|TBD|lorem ipsum)\b", "\n".join(line for _, line, c in rows if not c), re.I):
        add("placeholder", "warning", "Remove TODO/TBD/lorem ipsum placeholders before publishing.")

    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.line or 0))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lint a README for conversion: pitch, badges, install, quick start, links."
    )
    parser.add_argument("readme", nargs="?", default="README.md", help="path to the README (default: README.md)")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    parser.add_argument("--max-scroll", type=int, default=60, help="line by which the first code block should appear")
    args = parser.parse_args(argv)

    path = Path(args.readme)
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 2
    findings = lint(path.read_text(encoding="utf-8", errors="replace"), path.parent, args.max_scroll)
    counts = {s: sum(1 for f in findings if f.severity == s) for s in SEVERITY_ORDER}
    if args.json:
        print(json.dumps({"file": str(path), "counts": counts, "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        for f in findings:
            where = f"{path}:{f.line}" if f.line else str(path)
            print(f"{where}: {f.severity}: [{f.rule}] {f.message}")
        print(f"\n{counts['error']} error(s), {counts['warning']} warning(s), {counts['info']} suggestion(s)")
    failing = counts["error"] + (counts["warning"] if args.strict else 0)
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
