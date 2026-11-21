## What does this pull request do?

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Type

- [ ] New skill
- [ ] Improvement to an existing skill (instructions, references or script)
- [ ] Bug fix
- [ ] Repository tooling or documentation

## Checklist

- [ ] `python tools/validate_skills.py` passes
- [ ] `pytest` passes; every new or changed script has tests in `tests/test_<script>.py`
- [ ] `ruff check . && ruff format --check .` passes
- [ ] Scripts use only the Python 3.11+ standard library, support `--help`, and are
      read-only or dry-run by default (no network calls)
- [ ] Skill instructions ask the user before anything that posts, publishes, pushes or deletes
- [ ] New skills are listed in `.claude-plugin/marketplace.json` and the README table
- [ ] CHANGELOG.md updated under "Unreleased"
