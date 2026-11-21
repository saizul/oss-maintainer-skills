# README structure that converts

Visitors scan top to bottom and leave at the first point of confusion. Each section
answers the next question they have.

| # | Section | Question it answers | Keep it |
| --- | --- | --- | --- |
| 1 | Title + badges | Is this alive and trustworthy? | one line of badges |
| 2 | Pitch | What is it, for whom, why this one? | one sentence, then 1-3 more |
| 3 | Demo (optional) | What does it look like? | one GIF/SVG/screenshot, with alt text |
| 4 | Quick start | Can I try it in 60 seconds? | install + one command + its output |
| 5 | Features | What else can it do? | 4-8 bullets, benefit first |
| 6 | Usage / examples | How do I do my real task? | 2-5 realistic examples |
| 7 | Configuration | What can I tune? | table: option, default, meaning |
| 8 | FAQ | Why not X? Does it work on Y? | 3-8 questions people actually ask |
| 9 | Roadmap | Where is it going? Can I help? | short list, link issues |
| 10 | Contributing | How do I help? | 2-4 lines, link CONTRIBUTING.md |
| 11 | License | Can I use it? | one line, link LICENSE |

Add a table of contents after the pitch when there are more than about eight sections.

## The pitch

Formula: **name** + **category** + **what it does** + **for whom** + **differentiator**.

- Good: "`dbsnap` is a CLI that takes consistent, compressed snapshots of Postgres and
  MySQL databases to S3, with one config file and no agents."
- Weak: "A powerful, blazing-fast, next-generation tool for all your database needs."

Follow it with two or three sentences on the problem and the approach if needed. Put a
comparison with alternatives in the FAQ, not in the pitch.

## Quick start rules

- One code block for install, one for the first real use. Show the output.
- Use the package manager people expect for the ecosystem (`pip install`, `pipx install`,
  `npm install -g`/`npx`, `composer require`, `brew install`, `docker run`).
- No placeholders the reader must invent in the first command if a default works.
- If setup needs credentials, show an environment variable, never a real value.

## Examples

Pick tasks people search for ("convert X to Y", "run in CI", "use with Docker"). Each
example gets a heading phrased as the task, a code block and one sentence of context.

## Badges

Use shields.io or the provider's own badge. Replace OWNER/REPO/PACKAGE.

```markdown
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/PACKAGE)](https://pypi.org/project/PACKAGE/)
[![npm](https://img.shields.io/npm/v/PACKAGE)](https://www.npmjs.com/package/PACKAGE)
[![Packagist](https://img.shields.io/packagist/v/VENDOR/PACKAGE)](https://packagist.org/packages/VENDOR/PACKAGE)
[![Release](https://img.shields.io/github/v/release/OWNER/REPO)](https://github.com/OWNER/REPO/releases)
[![License](https://img.shields.io/github/license/OWNER/REPO)](LICENSE)
```

Do not add badges for things that are not true or not maintained (coverage you do not
measure, a chat you do not watch).

## FAQ ideas

- How is this different from `<popular alternative>`?
- Which platforms / runtime versions are supported?
- Is it production ready? (State the status honestly.)
- How do I upgrade? Where is the changelog?
- Does it send telemetry or make network calls?

## Common mistakes

- History or motivation essay before the install command.
- Screenshots without alt text, or a GIF larger than a few MB.
- Commands that only work on the author's machine (absolute paths, aliases).
- Copying the full CLI `--help` instead of curated examples.
- Outdated badges or links to a renamed default branch.
