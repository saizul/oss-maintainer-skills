# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-21

### Added

- `repo-health-check`: 0-100 repository health score with prioritized fixes (`repo_health.py`).
- `readme-writer`: README structure guide, template and linter (`readme_lint.py`).
- `contributor-onboarding`: CONTRIBUTING template, good first issue guide, label set
  generator and validator with a dry-run `gh` script (`labels.py`).
- `conventional-commits-release`: next semantic version and changelog section from
  Conventional Commits, with 0.x and prerelease rules (`next_version.py`).
- `github-actions-ci`: CI workflow generator for Python, Node.js and PHP with matrices
  and caching (`gen_ci.py`).
- `issue-triage`: triage queue from `gh issue list` JSON, reply templates and a stale
  policy (`triage_report.py`).
- `security-policy`: SECURITY.md and Dependabot config generator with a coverage check
  (`gen_security.py`).
- `release-checklist`: release preflight checks and registry publishing guide
  (`release_preflight.py`).
- `project-launch`: launch checklist, channel guide, post drafts and title linter
  (`launch_drafts.py`).
- Claude Code plugin marketplace manifests, `tools/validate_skills.py`, CI and release
  workflows.

[Unreleased]: https://github.com/saizul/oss-maintainer-skills/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/saizul/oss-maintainer-skills/releases/tag/v0.1.0
