---
name: repo-health-check
description: Scores a local repository's open-source health from 0 to 100 (README quality, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, issue and PR templates, CI, tests, changelog, badges, dependency updates) and prints a prioritized fix list. Use when the user asks to audit, review or "make this repo ready for open source", wants to know why a project gets no contributors, is preparing a public launch, or wants a health gate in CI.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Repository health check

Audit a repository the way a first-time visitor and a would-be contributor see it,
then fix the gaps in order of impact. The scoring script is read-only.

## When to use

- "Is this repo ready to open source / launch?"
- "Why doesn't anyone contribute?" or "audit my repo's community files"
- Before running the `project-launch` skill
- To add a minimum-health gate to CI

## When not to use

- Code quality, security or dependency audits of the source itself (use a linter or scanner).
- Repositories the user does not maintain: report findings, do not open PRs uninvited.

## Workflow

1. **Score.** Pass the repository path (`scripts/` is relative to this skill's directory):

   ```bash
   python3 scripts/repo_health.py .
   python3 scripts/repo_health.py . --json   # machine-readable, for summaries
   ```

2. **Read the fix list.** It is sorted by points available. Explain the top three to the
   user in one line each, with why it matters (see [scoring](references/scoring.md)).

3. **Decide scope with the user.** Ask which fixes to apply now. Default proposal:
   everything that is a missing file. README rewrites need user input (pitch, audience).

4. **Apply fixes**, delegating to the sibling skills when installed:

   | Gap | Fix with |
   | --- | --- |
   | README missing or thin, no badges | `readme-writer` |
   | CONTRIBUTING, labels, good first issues | `contributor-onboarding` |
   | SECURITY.md, Dependabot | `security-policy` |
   | No CI | `github-actions-ci` |
   | Issue/PR templates | [templates](references/templates.md) in this skill |
   | CHANGELOG | `conventional-commits-release` |

   For LICENSE: ask which license; never pick one silently. Fill the year and the
   copyright holder the user names. Do not invent an email address for any file.

5. **Re-score** and show before/after numbers.

6. **Optional CI gate.** Suggest adding a step such as
   `python3 path/to/repo_health.py . --min-score 80` (exit 1 below the threshold).
   Use `--skip badges` for private or internal repos.

## Output

- The score, grade and the fix list (text from the script, summarized, not pasted twice).
- A list of files you created or changed.
- Remaining items that need a human decision (license choice, pitch, contact channel).

## Checks and weights

| id | Points | Passes when |
| --- | --- | --- |
| readme | 10 | README exists with 150+ words |
| readme-sections | 15 | install, usage, contributing, license headings and a code block |
| badges | 5 | 2+ badges (CI, version, license) |
| license | 10 | LICENSE with full text |
| contributing | 8 | CONTRIBUTING.md in root, docs/ or .github/ |
| code-of-conduct | 5 | CODE_OF_CONDUCT.md |
| security | 7 | SECURITY.md |
| issue-templates | 5 | 2+ templates in .github/ISSUE_TEMPLATE/ |
| pr-template | 4 | pull_request_template.md |
| ci | 10 | a GitHub Actions workflow or other CI config |
| tests | 10 | a tests directory or test files |
| changelog | 4 | CHANGELOG.md (or CHANGES/HISTORY/NEWS) |
| gitignore | 3 | .gitignore |
| dependency-updates | 4 | dependabot.yml or Renovate config |

Score = points / max points of the checks that ran, scaled to 100.
Grades: A 90+, B 75+, C 60+, D 40+, F below.
