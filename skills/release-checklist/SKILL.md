---
name: release-checklist
description: Walks a maintainer through shipping a release safely - preflight checks (version consistent across pyproject.toml, package.json, composer.json, Cargo.toml and __version__ files, CHANGELOG entry present, clean git tree, tag free, branch in sync), then tagging, GitHub release notes, publishing to PyPI, npm, Packagist or crates.io, verifying the published package, and announcing it. Use when the user says "cut a release", "publish version X", "tag and release", "ship it", or asks what to check before releasing.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Release checklist

A release is a promise: the tag, the package, the changelog and the docs all describe
the same code. Check first, then perform each irreversible step only with the user's
go-ahead.

## When to use

- "Release 1.4.0", "cut a release", "publish to PyPI/npm", "tag and push"
- Before a first public release or launch
- Setting up a release workflow that attaches artifacts

## When not to use

- Deciding the version number: use `conventional-commits-release` first.
- Deploying a web service (that is a deploy, not a release of a versioned artifact).

## Workflow

### 1. Preflight (read-only)

`scripts/` is relative to this skill's directory.

```bash
python3 scripts/release_preflight.py . --version 1.4.0
python3 scripts/release_preflight.py . --version-file src/pkg/_version.py --json
```

It fails on: invalid semver, manifests that disagree, no CHANGELOG section (or an empty
one) for the version, missing LICENSE, uncommitted changes, an existing tag, or a branch
behind its upstream. It warns about non-release branches and unpushed commits.
Fix every FAIL before going on.

Then run the project's own test, lint and build commands (from CI or CONTRIBUTING.md)
and make sure the last CI run on the release branch is green:
`gh run list --branch main --limit 3`.

### 2. Tag and GitHub release (ask before each push)

```bash
git tag -a v1.4.0 -m "v1.4.0"
git push origin v1.4.0
gh release create v1.4.0 --title "v1.4.0" --notes-file notes.md   # notes = the CHANGELOG section
```

Use `--prerelease` for `-rc`/`-beta` versions and `--draft` to review first. If the
project's release workflow builds and publishes on tag push or on "release published",
stop here and watch it (`gh run watch`).

### 3. Publish packages (ask first; these are permanent)

See [publishing.md](references/publishing.md) for each registry. Prefer trusted
publishing from CI over local tokens. A version number can never be reused on PyPI,
npm or crates.io, even after deleting it.

### 4. Verify

- Install the published version in a clean environment and run `--version` or a smoke
  test (commands in [publishing.md](references/publishing.md#verify)).
- Check the release page, the package page (README renders, links work) and the docs.

### 5. Announce

Short release post: what is new for users, upgrade notes for breaking changes, thanks
to contributors (`gh api repos/OWNER/REPO/compare/v1.3.0...v1.4.0 --jq '.commits[].author.login' | sort -u`).
Post where the project's users are; for big releases use the `project-launch` skill.

### 6. After the release

- Add a fresh `## [Unreleased]` section to CHANGELOG.md.
- Close the milestone, and reply on issues fixed by the release.
- Bump to a development version if the project uses one.

## Output

- Preflight result, and each step you ran (or skipped) with its outcome.
- Links to the tag, release page and package page.
- Anything left for the user (announcement posts, settings).

## Release checklist (copy into the release PR or issue)

```markdown
- [ ] Version decided (semver) and bumped in all manifests
- [ ] CHANGELOG section written, dated, with upgrade notes for breaking changes
- [ ] CI green on the release branch; tests pass locally
- [ ] Preflight passes: release_preflight.py --version X.Y.Z
- [ ] Tag vX.Y.Z pushed; GitHub release created with notes
- [ ] Packages published (PyPI / npm / Packagist / crates.io / Docker)
- [ ] Published package installed and smoke-tested in a clean environment
- [ ] Docs updated; README badges show the new version
- [ ] Announcement posted; contributors thanked
- [ ] Unreleased section re-added to CHANGELOG
```
