#!/usr/bin/env python3
"""Draft launch posts (Show HN, Reddit, dev.to, short social post) and lint their titles.

  launch_drafts.py drafts --name NAME --url URL [--pitch "..." | --readme README.md]
                          [--tags python,cli] [--json]
  launch_drafts.py lint-title "Show HN: ..." [--site hn|reddit|devto] [--json]

Drafts are starting points with [FILL IN] markers for the parts only the author
can write (the story, the numbers, the trade-offs). Nothing is posted anywhere.

Exit codes: 0 = ok, 1 = title lint errors, 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HN_MAX = 80
REDDIT_MAX = 300
DEVTO_MAX_TAGS = 4
SOCIAL_MAX = 280
HYPE = (
    "best",
    "fastest",
    "ultimate",
    "revolutionary",
    "game-changer",
    "game changer",
    "blazing",
    "killer",
    "insane",
    "world's first",
    "10x",
)
EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿]")


def lint_title(title: str, site: str = "hn") -> list[dict]:
    issues: list[dict] = []

    def add(level: str, msg: str) -> None:
        issues.append({"level": level, "message": msg})

    t = title.strip()
    limit = {"hn": HN_MAX, "reddit": REDDIT_MAX, "devto": 128}[site]
    if not t:
        add("error", "Title is empty.")
        return issues
    if len(t) > limit:
        add("error", f"Title is {len(t)} characters; {site} allows {limit}.")
    if site == "hn":
        if not t.startswith("Show HN: "):
            add("error", "Show HN titles start with 'Show HN: ' (capital S, H, N, then a colon and a space).")
        if t.count("!"):
            add("error", "Drop the exclamation marks; HN strips or penalises them.")
    if EMOJI.search(t):
        add("error" if site == "hn" else "warning", "Remove emoji from the title.")
    lowered = t.lower()
    hype = [w for w in HYPE if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", lowered)]
    if hype:
        add("warning", f"Hype words read as marketing: {', '.join(hype)}. Say what it does instead.")
    letters = [c for c in t if c.isalpha()]
    caps_words = [
        w
        for w in re.findall(r"[A-Za-z]{4,}", t)
        if w.isupper() and w not in {"HTTP", "JSON", "YAML", "HTML", "REST", "SQLITE"}
    ]
    if letters and len(caps_words) >= 2:
        add("warning", f"Avoid shouting in capitals: {', '.join(caps_words)}.")
    if re.search(r"\b(please )?(upvote|star (it|us|this)|give (it|us) a star)\b", lowered):
        add("error", "Never ask for upvotes or stars in a title; it breaks HN and most subreddit rules.")
    return issues


def pitch_from_readme(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    seen_title = False
    para: list[str] = []
    in_code = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if in_code:
            continue
        if s.startswith("# ") and not seen_title:
            seen_title = True
            continue
        if s.startswith("#"):
            if para:
                break
            continue
        cleaned = re.sub(r"\[?!\[[^\]]*\]\([^)]*\)\]?(\([^)]*\))?", "", s)
        cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
        if not cleaned:
            if para:
                break
            continue
        if cleaned.startswith((">", "|", "-", "*")) and not para:
            cleaned = cleaned.lstrip(">|-* ").strip()
        para.append(cleaned)
    pitch = " ".join(para)
    pitch = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", pitch)
    pitch = re.sub(r"[*_`]", "", pitch)
    return pitch.strip()


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0].rstrip(".")


def hn_title(name: str, pitch: str) -> tuple[str, bool]:
    """Return (title, shortened). A long pitch is cut at a clause boundary, else at a word."""
    short = first_sentence(pitch)
    short = re.sub(rf"^{re.escape(name)}\s+(is|:|-|–)\s*", "", short, flags=re.I)
    short = short[0].upper() + short[1:] if short else short
    prefix = f"Show HN: {name} – "
    title = prefix + short
    if len(title) <= HN_MAX:
        return title, False
    head = title[:HN_MAX]
    cut = max(head.rfind(sep, len(prefix)) for sep in (", ", "; ", " with ", " for ", " that "))
    if cut > len(prefix) + 15:
        return head[:cut].rstrip(" ,;–"), True
    return head[: HN_MAX - 1].rsplit(" ", 1)[0].rstrip(",;:-– "), True


def slug_tags(tags: list[str]) -> list[str]:
    out = []
    for t in tags:
        s = re.sub(r"[^a-z0-9]", "", t.lower())
        if s and s not in out:
            out.append(s)
    return out[:DEVTO_MAX_TAGS]


def drafts(name: str, url: str, pitch: str, repo: str | None, tags: list[str]) -> dict:
    sentence = first_sentence(pitch)
    link = repo or url
    hn, shortened = hn_title(name, pitch)
    hn_lint = lint_title(hn, "hn")
    if shortened:
        hn_lint.append(
            {"level": "warning", "message": "The pitch was too long and was cut; rewrite the title by hand."}
        )
    first_word = sentence.split(" ", 1)[0] if sentence else ""
    lower = sentence[0].lower() + sentence[1:] if first_word in {"A", "An", "The"} else sentence
    hn_comment = f"""Hi HN, I built {name}, {lower}.

Why: [FILL IN: the problem you hit, in one or two sentences, and what you tried first]

How it works: [FILL IN: the interesting technical part, the trade-offs, what it does NOT do]

Try it: {url}
Source: {link}

It is free and open source. I would love feedback on [FILL IN: one specific question], and I'll be here to answer questions."""
    reddit_title = f"I built {name}, {lower}".rstrip(", ")
    reddit_body = f"""**What it is:** {pitch}

**Why I made it:** [FILL IN: the itch, briefly]

**What makes it different:** [FILL IN: 2-3 concrete points, with numbers if you have them]

**Status:** [FILL IN: alpha / stable, what is missing]

Repo: {link}

Feedback, bug reports and contributions are welcome. Happy to answer questions in the comments."""
    tag_list = slug_tags(tags)
    devto = f"""---
title: "Introducing {name}: {sentence}"
published: false
description: "{sentence.replace('"', "'")}"
tags: {", ".join(tag_list)}
canonical_url:
---

[FILL IN: a one-paragraph hook: the problem, told as a short story]

## What {name} does

{pitch}

## Quick start

```bash
[FILL IN: the install and first command from your README]
```

## How it works

[FILL IN: architecture, one diagram or code sample, trade-offs]

## What's next

[FILL IN: roadmap; link good first issues]

{name} is open source: {link}. Stars, issues and pull requests are all welcome.
"""
    social = f"{name}: {sentence}. Open source. {link}"
    if len(social) > SOCIAL_MAX:
        room = SOCIAL_MAX - len(f"{name}: . Open source. {link}") - 1
        social = f"{name}: {sentence[:room].rstrip()}… Open source. {link}"
    return {
        "show_hn": {"title": hn, "url": url, "first_comment": hn_comment, "title_lint": hn_lint},
        "reddit": {"title": reddit_title, "body": reddit_body, "title_lint": lint_title(reddit_title, "reddit")},
        "devto": {"markdown": devto, "tags": tag_list},
        "social": {"text": social, "length": len(social)},
    }


def format_drafts(d: dict) -> str:
    parts = [
        "=== Show HN ===",
        f"Title: {d['show_hn']['title']}",
        f"URL:   {d['show_hn']['url']}",
        "First comment (post it yourself right after submitting):",
        d["show_hn"]["first_comment"],
    ]
    for issue in d["show_hn"]["title_lint"]:
        parts.append(f"  title {issue['level']}: {issue['message']}")
    parts += ["", "=== Reddit ===", f"Title: {d['reddit']['title']}", "", d["reddit"]["body"]]
    parts += ["", "=== dev.to (save as draft) ===", d["devto"]["markdown"]]
    parts += ["=== Short social post ===", f"{d['social']['text']}  ({d['social']['length']} chars)"]
    return "\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Draft launch posts and lint launch titles. Posts nothing.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("drafts", help="print draft posts")
    d.add_argument("--name", required=True)
    d.add_argument("--url", required=True, help="where people can try it (repo, demo or docs URL)")
    src = d.add_mutually_exclusive_group(required=True)
    src.add_argument("--pitch", help="one or two sentences: what it is and who it is for")
    src.add_argument("--readme", help="take the pitch from the first paragraph of this README")
    d.add_argument("--repo", help="source repository URL if different from --url")
    d.add_argument("--tags", default="opensource", help="comma-separated dev.to tags (max 4 kept)")
    d.add_argument("--json", action="store_true")
    t = sub.add_parser("lint-title", help="check a title against the site's rules")
    t.add_argument("title")
    t.add_argument("--site", choices=["hn", "reddit", "devto"], default="hn")
    t.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "lint-title":
        issues = lint_title(args.title, args.site)
        if args.json:
            print(json.dumps({"title": args.title, "length": len(args.title), "issues": issues}, indent=2))
        else:
            for i in issues:
                print(f"{i['level']}: {i['message']}")
            print(f"{len(args.title)} chars, {'ok' if not issues else str(len(issues)) + ' issue(s)'}")
        return 1 if any(i["level"] == "error" for i in issues) else 0

    if args.readme:
        path = Path(args.readme)
        if not path.is_file():
            print(f"error: {path} not found", file=sys.stderr)
            return 2
        pitch = pitch_from_readme(path)
        if not pitch:
            print("error: could not find a pitch paragraph under the README title; pass --pitch", file=sys.stderr)
            return 2
    else:
        pitch = args.pitch.strip()
    result = drafts(args.name, args.url, pitch, args.repo, [x for x in args.tags.split(",") if x.strip()])
    print(json.dumps(result, indent=2) if args.json else format_drafts(result), end="" if not args.json else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
