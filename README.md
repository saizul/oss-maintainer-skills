# oss-maintainer-skills

[![CI](https://github.com/saizul/oss-maintainer-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/saizul/oss-maintainer-skills/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/saizul/oss-maintainer-skills)](https://github.com/saizul/oss-maintainer-skills/releases)
[![License: MIT](https://img.shields.io/github/license/saizul/oss-maintainer-skills)](LICENSE)
[![Stars](https://img.shields.io/github/stars/saizul/oss-maintainer-skills?style=social)](https://github.com/saizul/oss-maintainer-skills/stargazers)

**Agent Skills that help open-source maintainers grow and run their projects, for Claude
Code and Codex CLI.** Score repo health, write a README that converts, onboard
contributors, cut semver releases from Conventional Commits, generate CI, triage issues,
set up a security policy and launch on Show HN, Reddit and dev.to.

Each skill is a step-by-step workflow for your coding agent, backed by small, tested,
standard-library Python scripts that do the parts that must be exact.

- [Skills](#skills)
- [Install for Claude Code](#install-for-claude-code)
- [Install for Codex CLI](#install-for-codex-cli)
- [Usage examples](#usage-examples)
- [How skills work](#how-skills-work)
- [Run the scripts without an agent](#run-the-scripts-without-an-agent)
- [FAQ](#faq)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Skills

| Skill | What it does | Example prompt |
| --- | --- | --- |
| [repo-health-check](skills/repo-health-check/SKILL.md) | Scores a repo 0-100 (README, LICENSE, community files, templates, CI, tests, badges, Dependabot) and fixes gaps in order of impact | "Is this repo ready to open source?" |
| [readme-writer](skills/readme-writer/SKILL.md) | Writes or restructures a README: pitch, badges, 60-second quick start, examples, FAQ; lints sections, links, TOC anchors and alt text | "Rewrite my README so people get it in 30 seconds" |
| [contributor-onboarding](skills/contributor-onboarding/SKILL.md) | CONTRIBUTING.md from your real commands, a consistent label set (dry-run `gh` script), good first issues | "Help me get my first contributors" |
| [conventional-commits-release](skills/conventional-commits-release/SKILL.md) | Next semver and a changelog section from Conventional Commits, with 0.x and `-rc.N` rules, `git revert` commits and linked PR numbers | "What's the next version? Write the changelog" |
| [github-actions-ci](skills/github-actions-ci/SKILL.md) | Generates GitHub Actions CI for Python, Node.js (npm/pnpm/yarn) or PHP with matrices and caching | "Add CI that tests Python 3.11 to 3.14" |
| [issue-triage](skills/issue-triage/SKILL.md) | Triage queue from `gh issue list` (untriaged, needs-info, missing repro, duplicates, stale), reply templates, stale policy | "Triage my open issues" |
| [security-policy](skills/security-policy/SKILL.md) | SECURITY.md with private vulnerability reporting, Dependabot config for every ecosystem, coverage check, report handling | "Add a security policy and Dependabot" |
| [release-checklist](skills/release-checklist/SKILL.md) | Preflight (versions agree, changelog entry, clean tree, tag free), tag, GitHub release, publish to PyPI/npm/Packagist/crates.io, verify | "Release 1.4.0" |
| [project-launch](skills/project-launch/SKILL.md) | Launch checklist, where and how to post, drafts for Show HN, Reddit, dev.to and social, title linting | "Help me launch this on Hacker News" |

The skills hand off to each other: `repo-health-check` points to `readme-writer`,
`security-policy` and `github-actions-ci`; `conventional-commits-release` feeds
`release-checklist`; `project-launch` starts with a health check.

## Install for Claude Code

### As a plugin (recommended)

Inside Claude Code:

```text
/plugin marketplace add saizul/oss-maintainer-skills
/plugin install oss-maintainer-skills@oss-maintainer-skills
```

Or from your shell:

```bash
claude plugin marketplace add saizul/oss-maintainer-skills
claude plugin install oss-maintainer-skills@oss-maintainer-skills
```

Claude picks a skill automatically when your request matches its description. You can
also call one directly, for example `/oss-maintainer-skills:repo-health-check`.
Update later with `/plugin marketplace update oss-maintainer-skills`.

### Manual copy

Copy the skills you want into your personal skills folder (all projects) or into a
project's `.claude/skills/` folder (shared with your team through git):

```bash
git clone https://github.com/saizul/oss-maintainer-skills.git
mkdir -p ~/.claude/skills
cp -r oss-maintainer-skills/skills/* ~/.claude/skills/
# or, per project:
mkdir -p .claude/skills && cp -r oss-maintainer-skills/skills/repo-health-check .claude/skills/
```

Each release also has one zip per skill and an all-skills zip under
[Releases](https://github.com/saizul/oss-maintainer-skills/releases).

## Install for Codex CLI

Codex reads skills from `.agents/skills/` in your repository (and parent folders up to
the repository root) and from `~/.agents/skills/` for all projects
([Codex skills docs](https://developers.openai.com/codex/skills)):

```bash
git clone https://github.com/saizul/oss-maintainer-skills.git
mkdir -p ~/.agents/skills
cp -r oss-maintainer-skills/skills/* ~/.agents/skills/
# or, per project:
mkdir -p .agents/skills && cp -r oss-maintainer-skills/skills/issue-triage .agents/skills/
```

Restart Codex if a new skill does not show up. Invoke one explicitly with `/skills` or
by typing `$` and the skill name (for example `$release-checklist`), or just describe
the task. [AGENTS.md](AGENTS.md) has notes for Codex and other agents.

## Usage examples

**Audit and fix a repository before making it public**

```text
Run a health check on this repo and fix everything that's just a missing file.
```

The agent runs `repo_health.py`, shows the score and the top fixes, asks you to pick a
license and confirm the contact channel, writes the files, and re-scores.

**Cut a release**

```text
What should the next version be? Update the changelog, then walk me through releasing it.
```

`next_version.py --git` proposes the bump and notes, the agent polishes them into
CHANGELOG.md, `release_preflight.py` checks versions, changelog and git state, and
the agent asks before tagging, pushing and publishing.

**Weekly triage**

```text
Export my open issues and tell me what needs attention. Draft replies, don't post.
```

**Launch**

```text
Draft a Show HN post and a Reddit post for this project.
```

`launch_drafts.py` produces drafts with `[FILL IN]` markers for your own story and
lints the titles; you post them yourself.

## How skills work

A skill is a folder with a `SKILL.md`: YAML frontmatter (`name`, `description`) and
Markdown instructions, plus optional `scripts/`, `references/` and `assets/`. The agent
loads only the names and descriptions at startup, reads the full `SKILL.md` when a task
matches, and opens references only when a step needs them (progressive disclosure).
The format is the open [Agent Skills](https://agentskills.io) standard, which is why the
same folders work in Claude Code and Codex.

Design rules in this repository:

- **Safe by default.** Scripts only read, or print to stdout. Writing needs `--write` or
  `--output` and never overwrites without `--force`. No script calls the network.
- **The user approves public actions.** Skills draft comments, labels, releases and
  posts; the agent asks before posting, publishing, pushing, tagging or deleting.
- **Exact where it matters.** Version math, YAML generation, scoring and validation are
  done by tested code, not by the model's memory.

## Run the scripts without an agent

Every script works on its own with Python 3.11+ and has `--help`:

```bash
python3 skills/repo-health-check/scripts/repo_health.py . --min-score 80
python3 skills/readme-writer/scripts/readme_lint.py README.md --strict
python3 skills/conventional-commits-release/scripts/next_version.py --git --json
python3 skills/github-actions-ci/scripts/gen_ci.py generate . --versions 3.12,3.13
python3 skills/security-policy/scripts/gen_security.py check .
python3 skills/release-checklist/scripts/release_preflight.py . --version 1.4.0
```

`repo_health.py --min-score` and `readme_lint.py --strict` make good CI gates.

## FAQ

**Do I need Claude Code or Codex?**
No. The scripts run anywhere with Python 3.11+, and the SKILL.md files read fine as
checklists. The agents make the workflows hands-off.

**Will the agent post on GitHub, Hacker News or Reddit for me?**
No. The skills draft; the agent must ask before any public action, and the launch
skill never posts. Read-only `gh` commands (listing issues, runs) are used freely.

**Does anything leave my machine?**
The scripts make no network calls. The agent may run `gh` commands you approve.

**Which languages and ecosystems are supported?**
CI generation: Python, Node.js, PHP. Release preflight: pyproject.toml, package.json,
composer.json, Cargo.toml and `__version__` files. Dependabot: pip, npm, composer,
github-actions, docker, gomod, cargo, bundler, maven, gradle, nuget. The other skills
are language-agnostic.

**Can I install only some skills?**
Yes, with the manual copy method. The plugin installs all nine.

**How is this different from release-please or semantic-release?**
Those are release bots. `conventional-commits-release` gives your agent the same
version logic for interactive use, and the result is reviewed by you before anything
is tagged. Use both if you like.

## Roadmap

Ideas for new skills; each is a good first contribution (see
[CONTRIBUTING.md](CONTRIBUTING.md#write-a-new-skill)):

- [ ] `funding-setup`: FUNDING.yml, GitHub Sponsors and Open Collective profile text
- [ ] `docs-site`: scaffold MkDocs or Docusaurus docs with versioning and deploy
- [ ] `governance`: MAINTAINERS.md, decision process, adding and retiring maintainers
- [ ] `pr-review`: friendly first-PR review checklists and reply templates
- [ ] `community-metrics`: monthly report of contributors, response times and stars from `gh` exports
- [ ] `deprecation-policy`: deprecating APIs and versions with warnings and timelines
- [ ] `hacktoberfest-prep`: topics, labels and a batch of good first issues
- [ ] `license-chooser`: compare licenses and check dependency license compatibility

## Contributing

Contributions are welcome, from typo fixes to new skills. Read
[CONTRIBUTING.md](CONTRIBUTING.md) for the skill template, the validator and a list of
good first issues, and follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report
security issues privately as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Saizul Amin
