# Contributing to oss-maintainer-skills

Thanks for helping! New skills, sharper instructions, better checks in the scripts and
bug reports are all welcome. You do not need to be an expert maintainer: if a skill
gave you bad advice, that report is valuable.

- [Ways to contribute](#ways-to-contribute)
- [Good first issues](#good-first-issues)
- [Development setup](#development-setup)
- [Repository layout](#repository-layout)
- [Write a new skill](#write-a-new-skill)
- [Script guidelines](#script-guidelines)
- [Pull request process](#pull-request-process)

## Ways to contribute

| Time | Idea |
| --- | --- |
| 10 minutes | Fix a typo, clarify a step, add a FAQ entry to the README |
| 30 minutes | Add a missing check or test case to a script |
| 1-2 hours | One of the good first issues below |
| Larger | A new skill (open a "New skill proposal" issue first) |

Comment on an issue before you start so nobody else picks the same one.

## Good first issues

Each of these is self-contained and touches one or two files plus tests.

1. **repo-health-check: detect `FUNDING.yml`.** Add an optional, low-weight check for
   `.github/FUNDING.yml` in `repo_health.py`, with a test and a row in the SKILL.md table.
2. **repo-health-check: `--format markdown`.** Print the report as a Markdown table that
   can be pasted into an issue.
3. **readme-writer: detect a stale default branch.** Warn when README links contain
   `/blob/master/` but the repository uses `main` (pass `--branch main`).
4. **readme-writer: image size warning.** Warn when a relative image is larger than 5 MB.
5. **contributor-onboarding: `labels.py diff`.** Compare a labels JSON with the output
   of `gh label list --json name,color,description` (read from a file) and print
   create/update/extra lists.
6. **conventional-commits-release: `--scopes` filter.** Only count commits whose scope is
   in a given list (useful in monorepos).
7. **github-actions-ci: Go support.** Detect `go.mod` and generate a job with
   `actions/setup-go`, module caching and `go test ./...`.
8. **issue-triage: label age.** Add a bucket for issues labeled `in-progress` with no
   activity for 30 days.
9. **security-policy: `uv` and `pnpm` notes.** Detect `uv.lock` and mention Dependabot's
   `uv` ecosystem in the generated config comment.
10. **release-checklist: check `CITATION.cff`.** If present, its `version` must match.
11. **project-launch: Bluesky and Mastodon limits.** Add `--site bluesky` (300 chars) and
    `--site mastodon` (500 chars) to `lint-title`.

## Development setup

Requirements: Python 3.11+ and git.

```bash
git clone https://github.com/saizul/oss-maintainer-skills.git
cd oss-maintainer-skills
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

Run everything CI runs:

```bash
ruff check .
ruff format --check .
python tools/validate_skills.py
pytest
```

To try your changes in Claude Code without publishing, load the repository as a local
marketplace: `claude plugin marketplace add ./` from the repository root, then
`claude plugin install oss-maintainer-skills@oss-maintainer-skills`. Or copy one skill
folder into `~/.claude/skills/`.

## Repository layout

```
.claude-plugin/
  marketplace.json     # Claude Code marketplace; lists every skill
  plugin.json          # plugin manifest (name, version, author)
skills/<name>/
  SKILL.md             # frontmatter + instructions (required)
  scripts/             # deterministic helpers, Python stdlib only
  references/          # detail loaded on demand
  assets/              # templates the skill copies
templates/skill/       # starting point for new skills
tests/                 # one test file per script, plus validator tests
tools/validate_skills.py
```

## Write a new skill

1. Open a "New skill proposal" issue describing when an agent should use it.
2. Copy the template: `cp -r templates/skill skills/your-skill-name`.
3. Fill in the frontmatter:
   - `name`: equal to the folder name; lowercase letters, digits and single hyphens;
     at most 64 characters.
   - `description`: at most 1024 characters. First say **what** it does (concrete
     outputs), then **when** to use it, starting with "Use when". Include the words users
     actually type ("changelog", "Dependabot", "Show HN").
4. Write the body with the required sections: `## When to use`, `## When not to use`,
   `## Workflow`, `## Output`. Imperative steps, exact commands, decision points,
   checklists. Keep it under 400 lines; move long material to `references/*.md` and link it.
5. Add a script only where it makes the result more reliable (a validator, scanner or
   generator). Follow the [script guidelines](#script-guidelines).
6. Add the skill to `.claude-plugin/marketplace.json` (`plugins[0].skills`), the README
   table and CHANGELOG.md.
7. Run the validator and tests.

Good skills are opinionated about the workflow, honest about limits, and make the agent
ask before anything that acts in public (posting, publishing, pushing, deleting).

## Script guidelines

- Python 3.11+ standard library only (or POSIX shell). No network calls unless the
  skill's purpose requires it, and then only behind an explicit opt-in flag.
- `--help` via argparse; `--json` for machine-readable output when the script reports.
- Exit codes: `0` success, `1` findings or a refused write, `2` usage error.
- Read-only by default. Write files only with `--write`/`--output`, never overwrite
  without `--force`. Never print secrets.
- Tests in `tests/test_<script>.py` using `tmp_path` fixtures; no network, no real
  credentials. Test both the functions and the CLI (exit codes, JSON shape).

## Pull request process

1. Fork, branch (`git checkout -b feat/skill-name`), and commit with
   [Conventional Commits](https://www.conventionalcommits.org/) (`feat(issue-triage): ...`).
2. Run the checks above and fill in the pull request template.
3. A maintainer reviews within a few days. Small focused PRs are merged fastest.

By contributing you agree that your contribution is licensed under the MIT License and
that you follow the [Code of Conduct](CODE_OF_CONDUCT.md).
