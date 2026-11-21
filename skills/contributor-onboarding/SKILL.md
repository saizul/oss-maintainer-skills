---
name: contributor-onboarding
description: Sets up a repository to attract and keep first-time contributors - writes CONTRIBUTING.md from the project's real setup and test commands, generates and validates a consistent GitHub label set (type, status, priority, good first issue, help wanted) with a dry-run script for gh, and turns vague issues into well-scoped good first issues. Use when the user wants more contributors, asks for a CONTRIBUTING guide, labels, or good first issues, or prepares for Hacktoberfest or a launch.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Contributor onboarding

New contributors need three things: a path (CONTRIBUTING.md), a map (labels) and a
first step (good first issues). Build all three from the project's real commands.

## When to use

- "Write a CONTRIBUTING.md" / "how do I get contributors?"
- Creating or cleaning up GitHub labels
- Writing good first issues, or preparing for Hacktoberfest or a launch

## When not to use

- Governance documents for foundations (GOVERNANCE.md, charters): out of scope.
- Code of conduct text: adopt the Contributor Covenant as-is; do not rewrite it.

## Workflow

### 1. CONTRIBUTING.md

1. Find the real commands: setup (`pip install -e ".[dev]"`, `npm ci`, `composer install`),
   tests, lint/format, build, docs. Read CI workflows; they are the source of truth.
2. Copy [the template](assets/CONTRIBUTING.template.md) and fill every placeholder.
   Run each command you document, or say clearly which ones you could not run.
3. Keep it scannable: ways to contribute (by time needed), setup, tests, style,
   commit convention, PR process, where to ask. Link CODE_OF_CONDUCT.md and SECURITY.md.
4. Add 5-10 concrete starter tasks under "Good first issues" or link the label.

### 2. Labels

`scripts/` is relative to this skill's directory. The script never calls GitHub itself.

```bash
python3 scripts/labels.py generate > labels.json                  # default set
python3 scripts/labels.py generate --area cli --area docs --prefixed > labels.json
python3 scripts/labels.py validate labels.json                    # exit 1 on problems
python3 scripts/labels.py commands labels.json --repo OWNER/NAME > apply-labels.sh
```

Show the user `apply-labels.sh` and **ask before running it**: it creates or updates
labels on GitHub (`gh label create ... --force`). It never deletes labels. If the user
wants old labels removed, list them with `gh label list` and confirm each deletion.

Keep GitHub's names `good first issue` and `help wanted` unchanged: GitHub and
third-party sites use them to surface beginner tasks.

### 3. Good first issues

Rewrite candidate issues with [the guide](references/good-first-issues.md). Each needs:
context, the exact files to touch, acceptance criteria, how to test, and an offer of
help. Ask before editing or labeling issues on GitHub; offer the text as a draft first.

## Output

- CONTRIBUTING.md (new or updated) and a list of commands verified vs. not verified.
- `labels.json` and `apply-labels.sh` (not executed unless the user approved).
- Drafted good first issues as Markdown, ready to paste or to create with
  `gh issue create --title ... --body-file ... --label "good first issue"` after approval.

## Default label set

| Group | Labels |
| --- | --- |
| type | bug, enhancement, documentation, question, performance, refactor |
| contributor | good first issue, help wanted |
| status | needs-triage, needs-repro, needs-info, confirmed, in-progress, blocked, stale |
| priority | priority: critical, priority: high, priority: low |
| resolution | duplicate, invalid, wontfix |
| dependencies | dependencies, security, breaking-change |

`--prefixed` switches to `type: bug`, `status: needs triage` style names. GitHub limits
label names to 50 characters and descriptions to 100; `validate` checks both, plus
6-digit hex colors and case-insensitive duplicates.
