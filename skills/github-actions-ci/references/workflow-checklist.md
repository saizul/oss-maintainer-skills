# Workflow review checklist

Use this when reviewing a generated or existing workflow.

## Safety

- [ ] Top-level `permissions:` is set, `contents: read` by default. Grant `write`
      scopes per job only where needed (releases, comments, packages).
- [ ] No `pull_request_target` with a checkout of the PR head (it runs untrusted code
      with secrets). Use `pull_request` for tests.
- [ ] Secrets are never echoed and not passed to steps that run PR code from forks.
- [ ] No `${{ github.event.pull_request.title }}` or other user-controlled text directly
      inside `run:`; pass it through `env:` and quote it.
- [ ] Third-party actions are from trusted publishers; consider pinning to a commit SHA
      for sensitive repositories.

## Speed

- [ ] Dependency caching is on (setup-* `cache:` input or `actions/cache`).
- [ ] `concurrency` cancels superseded runs.
- [ ] Lint runs once, not on every matrix entry, when it is slow (split into a
      separate `lint` job on one version).
- [ ] `paths-ignore` for docs-only changes if the test suite is long, e.g.
      `paths-ignore: ['**.md', 'docs/**']` under `pull_request`.
- [ ] `timeout-minutes` set on long jobs so a hang does not burn the full 6 hours.

## Coverage of versions

- [ ] Matrix matches the versions the project claims to support, and includes the
      newest release.
- [ ] `fail-fast: false` so one failing version does not hide the others.
- [ ] Windows/macOS runners only if users run there (they are slower).

## Reliability

- [ ] Lockfile-respecting installs (`npm ci`, `--frozen-lockfile`, `composer install`).
- [ ] Tests do not depend on the network or on wall-clock time.
- [ ] Required status checks are configured in branch protection after the first green run.

## Useful additions

Service container (Postgres) for integration tests:

```yaml
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
```

Separate lint job:

```yaml
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: "3.13"
      - run: pip install ruff && ruff check . && ruff format --check .
```
