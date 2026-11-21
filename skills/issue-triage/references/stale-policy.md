# Stale policy

A stale policy exists to make decisions, not to make issues disappear. Publish it in
CONTRIBUTING.md so contributors know what to expect.

## Recommended policy text

```markdown
## Issue lifecycle

- New issues get a first response within 5 working days.
- Issues labeled `needs-info` or `needs-repro` are closed after 14 days without a
  reply from the reporter. Reopen any time with the requested details.
- Other issues with no activity for 60 days get a `stale` label and a comment. They
  are closed 14 days later unless someone comments.
- Confirmed bugs, `security`, `pinned` and `priority: critical` issues are never closed
  automatically.
```

## Optional: actions/stale

Only add automation after the backlog has been triaged once by hand; otherwise the
bot closes real bugs. Check the action's README for the current major version.

```yaml
name: Stale
on:
  schedule:
    - cron: "30 1 * * *"
  workflow_dispatch:
permissions:
  issues: write
  pull-requests: write
jobs:
  stale:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/stale@v10
        with:
          days-before-stale: 60
          days-before-close: 14
          stale-issue-label: stale
          exempt-issue-labels: "confirmed,security,pinned,priority: critical"
          stale-issue-message: >
            This issue has had no activity for 60 days. Is it still relevant on the
            latest version? Comment to keep it open; otherwise it closes in 14 days.
          close-issue-message: >
            Closing after 74 days without activity. Reopen with new details any time.
          days-before-pr-stale: -1
          days-before-pr-close: -1
```

Setting the PR values to `-1` leaves pull requests alone; ping PR authors by hand.

## Weekly routine (30 minutes)

1. Export issues and run `triage_report.py --markdown`.
2. Respond to every untriaged issue (even "thanks, will look this week").
3. Close overdue `needs-info` issues with the "no response" reply.
4. Pick two stale issues and make a real decision: close, `help wanted`, or schedule.
5. Refill good first issues to 5-10 open.
