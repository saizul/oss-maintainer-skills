---
name: conventional-commits-release
description: Computes the next semantic version and a Keep a Changelog section from Conventional Commits (feat, fix, perf, revert, breaking changes with ! or BREAKING CHANGE footers), including 0.x rules and prereleases like rc.1, and helps write commit messages that follow the spec. Use when the user asks what the next version should be, wants release notes or a CHANGELOG entry from git history, asks how to word a commit, or wants to adopt Conventional Commits and semver in a project.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Conventional Commits release

Commit messages carry the release information: `feat` means a new minor version, `fix`
a patch, and `!` or `BREAKING CHANGE:` a major. The script turns history into a version
number and a changelog section. It only reads git; it never tags or commits.

## When to use

- "What version should I release next?" / "write the changelog for this release"
- "How should I word this commit?"
- Adopting Conventional Commits and semantic versioning in a project

## When not to use

- Projects that version by date (CalVer) or never tag releases: the bump logic does not apply.
- Monorepos with independently versioned packages: run per package with `--since`
  on that package's tag, or use a dedicated tool (release-please, changesets).

## Workflow

1. **Collect commits** since the last release tag (`scripts/` is relative to this skill):

   ```bash
   python3 scripts/next_version.py --git                    # since latest v* tag
   python3 scripts/next_version.py --git --since v1.4.0     # explicit start
   python3 scripts/next_version.py --git --json             # for further processing
   ```

   Without tags the current version defaults to 0.0.0; pass `--current 1.4.0` when the
   version lives only in a manifest.

2. **Review the result with the user.** Check the `non_conventional` list in `--json`
   output: those commits are not counted toward the bump. Read them; if one is really a
   feature or a breaking change, say so and propose the corrected bump.

3. **Polish the notes.** The script output is a draft. Rewrite subjects so users
   understand them (what changed for them, not how), merge duplicates, and put upgrade
   instructions under "Breaking changes". Keep the version heading format
   `## [X.Y.Z] - YYYY-MM-DD`.

4. **Update CHANGELOG.md.** Insert the section below `## [Unreleased]` (create that
   heading if missing), keep older sections intact, and update the compare links at the
   bottom if the file uses them.

5. **Bump manifests** (`pyproject.toml`, `package.json`, ...) to the same version, then
   hand over to the `release-checklist` skill. Do not create the tag yourself unless the
   user asks.

## Bump rules

| Commits since last tag | 1.x and later | 0.x (default) |
| --- | --- | --- |
| any `!` or `BREAKING CHANGE:` | major | minor |
| any `feat` | minor | minor |
| only `fix`, `perf`, `revert` | patch | patch |
| only `docs`, `chore`, `ci`, `test`, `style`, `refactor`, `build` | none | none |

- `--no-zero-major-rule`: let a breaking change on 0.x go to 1.0.0.
- `--pre rc`: produce `1.5.0-rc.1`; running again from `1.5.0-rc.1` gives `1.5.0-rc.2`.
  Without `--pre`, a prerelease is finished: `1.5.0-rc.2` + fix gives `1.5.0`.
- `--fail-if-none` exits 1 when nothing warrants a release (useful in CI).
- `--repo-url https://github.com/OWNER/REPO` links commit hashes and `(#123)` pull request
  references (as added by squash merges).
- `git revert` commits (`Revert "feat: add x"`) count as `revert` (patch bump) and are
  listed under Reverts with the original header.
- `--include docs,other` also lists documentation and other commits.

## Writing commit messages

Format: `type(optional scope)!: imperative summary` then an optional body and footers.
See [the cheat sheet](references/commit-cheatsheet.md) for types, examples and the
breaking-change footer. When asked to word a commit, read the staged diff
(`git diff --cached`) and propose one message; do not commit unless asked.

## Output

- Current version, bump, next version and tag name.
- The edited changelog section, and which commits you reworded or reclassified.
