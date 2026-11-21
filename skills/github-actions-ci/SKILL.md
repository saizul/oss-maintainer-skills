---
name: github-actions-ci
description: Generates a GitHub Actions CI workflow for Python, Node.js (npm, pnpm, yarn) or PHP (Composer) projects by detecting manifests, lockfiles, dev tools and scripts - with a runtime version matrix, dependency caching, least-privilege permissions and concurrency cancelling - and reviews existing workflows for common mistakes. Use when the user asks to add CI, set up GitHub Actions, test on several Python/Node/PHP versions, speed up or fix a slow or flaky workflow, or make pull requests run tests automatically.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# GitHub Actions CI

Every pull request should get lint and test results in a few minutes, on every
supported runtime version, without the maintainer doing anything.

## When to use

- A repository has no CI, or CI only runs on one version
- "Add GitHub Actions", "run tests on PRs", "test on Python 3.11-3.14 / Node 22 and 24 / PHP 8.2-8.4"
- Reviewing or speeding up an existing workflow

## When not to use

- Deployment or release pipelines with secrets (write them by hand; see the
  `release-checklist` skill for release workflows).
- GitLab CI, CircleCI and others: the generated YAML is GitHub Actions only.

## Workflow

1. **Detect** what the project uses (`scripts/` is relative to this skill):

   ```bash
   python3 scripts/gen_ci.py detect .
   ```

   It reports the language, install commands, lint and test commands it found
   (ruff/flake8/mypy/pytest; npm/pnpm/yarn scripts `lint`, `typecheck`, `build`, `test`;
   phpstan/phpcs/php-cs-fixer/phpunit/pest or `composer test`). Confirm that these are the
   commands the maintainers actually run; check CONTRIBUTING.md and the Makefile.

2. **Choose versions** with the user. Defaults: Python 3.11-3.14, Node 22 and 24, PHP
   8.2-8.4. Match the versions the project claims to support (`requires-python`,
   `engines.node`, `require.php`) and drop end-of-life versions.

3. **Generate**:

   ```bash
   python3 scripts/gen_ci.py generate . --versions 3.12,3.13,3.14
   python3 scripts/gen_ci.py generate . --lang node --os ubuntu-latest,windows-latest
   python3 scripts/gen_ci.py generate . --output .github/workflows/ci.yml   # refuses to overwrite
   ```

   For a repository with several languages, run once per language with `--lang` and
   rename the jobs, or write separate workflow files.

4. **Review the YAML** against [the checklist](references/workflow-checklist.md) and
   adjust: services (Postgres, Redis), extra build steps, coverage upload. Keep
   `permissions: contents: read` unless a step needs more.

5. **Verify.** Run the same install and test commands locally. If `actionlint` is
   installed, run it on the file. After pushing, check the run with
   `gh run list --workflow ci.yml` and `gh run view --log-failed`.

6. **Add the badge** to the README:
   `[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)`

## Output

- `.github/workflows/ci.yml` (or the YAML in chat if the user only wants to see it).
- What was detected, what you changed by hand, and anything not verified locally.

## What the generated workflow contains

- Triggers: push to the default branch, pull requests, manual `workflow_dispatch`.
- `concurrency` with `cancel-in-progress` so a new push cancels the old run.
- Matrix over runtime versions and runner OSes with `fail-fast: false`.
- Caching: `setup-python` pip cache keyed on requirements/pyproject; `setup-node` cache
  for npm/pnpm/yarn when a lockfile exists; Composer cache directory with `actions/cache`.
- Installs with lockfile-respecting commands (`npm ci`, `pnpm install --frozen-lockfile`,
  `composer install --prefer-dist`).
- Action versions: `actions/checkout@v7`, `actions/setup-python@v7`,
  `actions/setup-node@v7`, `actions/cache@v6`, `shivammathur/setup-php@v2`,
  `pnpm/action-setup@v6`. Dependabot (`security-policy` skill) keeps them current.
