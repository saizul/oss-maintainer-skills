# Writing good first issues

A good first issue is a task a newcomer can finish in one sitting without knowing the
codebase. The maintainer does the hard part (scoping and pointing at the code) so the
contributor can do the fun part.

## Pick the right tasks

Good candidates:

- A missing test case for existing behaviour
- A clearer error message, with the exact message and location
- A small, specified option or flag that follows an existing pattern
- Documentation: a missing example, an FAQ entry, a broken link
- A lint rule, typo or deprecation warning with a known fix

Bad candidates: anything needing design decisions, cross-cutting refactors, flaky test
hunts, security fixes, or "investigate why X is slow".

## Template

```markdown
### Context
One or two sentences: what the user sees today and why it matters.

### What to change
- In `src/pkg/module.py`, function `parse_args()`, add ...
- Follow the pattern used by `--existing-flag` (line ~120).

### Acceptance criteria
- [ ] `tool --new-flag` does X
- [ ] A test in `tests/test_module.py` covers the new case
- [ ] README option table updated

### How to test
    pip install -e ".[dev]"
    pytest tests/test_module.py -k new_flag

### Need help?
Comment here and a maintainer will answer within a few days. First time contributing?
See CONTRIBUTING.md.
```

## Rules of thumb

- Name exact files and functions. "Somewhere in the parser" is not a first issue.
- One issue, one change. Split anything with "and" in the title.
- Keep 5-10 open good first issues at any time; replenish after each is taken.
- Reply to a "can I take this?" comment within 48 hours, assign the person, and
  unassign politely after two weeks of silence.
- Thank first-time contributors in the PR and in release notes.
- Label `good first issue` only when the issue meets the template; otherwise use
  `help wanted`.

## Rewriting a vague issue

Before: "CLI should support config files."

After: "Read defaults from `.toolrc.toml`" with context (users repeat the same flags),
what to change (`load_config()` in `cli.py`, merge before argparse defaults, `tomllib`),
acceptance criteria (flag beats config, config beats default, missing file is fine),
test command, and the help offer.
