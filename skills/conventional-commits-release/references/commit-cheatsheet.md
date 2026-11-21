# Conventional Commits cheat sheet

Spec: https://www.conventionalcommits.org/en/v1.0.0/ - Semantic Versioning: https://semver.org/

```
<type>[optional scope][!]: <description>

[optional body]

[optional footer(s)]
```

## Types

| Type | Use for | Release |
| --- | --- | --- |
| feat | a new user-visible capability | minor |
| fix | a bug fix | patch |
| perf | a performance improvement | patch |
| revert | reverting an earlier commit | patch |
| docs | documentation only | none |
| refactor | code change that neither fixes nor adds | none |
| test | adding or fixing tests | none |
| build | build system, packaging, dependencies | none |
| ci | CI configuration | none |
| chore | maintenance that fits nowhere else | none |
| style | formatting, whitespace | none |

Only `feat` and `fix` are defined by the spec; the rest follow the widely used Angular
convention. Breaking changes can use any type.

## Examples

```
feat(cli): add --json output to the report command
fix: handle empty input files without crashing
perf(parser): cache compiled patterns
docs: add FAQ entry about Windows paths
feat!: drop support for Python 3.10
```

With a body and a breaking-change footer:

```
refactor(config)!: rename `timeout` to `timeout_seconds`

The old name was ambiguous about units.

BREAKING CHANGE: rename `timeout` to `timeout_seconds` in config files.
Closes #142
```

## Writing good descriptions

- Imperative mood, lower case, no trailing period: "add", not "added" or "adds".
- Say what changes for the user: "fix: keep file permissions when copying",
  not "fix: change mode param".
- Keep the header under about 72 characters; details go in the body.
- One logical change per commit. If you need "and", consider two commits.

## Squash merges

With squash merging, the pull request title becomes the commit message. Ask
contributors to use a Conventional Commits PR title, or edit it when merging.
