# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## What counts as a vulnerability

The skills run on the user's machine through an AI coding agent, so we care about:

- A helper script that writes, deletes or overwrites files it was not asked to
  (all scripts are read-only or print-only unless `--write`/`--output` is given)
- A script that makes network calls, runs git commands that change state, or executes
  content from the files it reads (issue bodies, READMEs, manifests)
- Shell or command injection in generated output, for example in the
  `gh label create` script produced by `labels.py`
- Skill instructions that tell an agent to post, publish, push or delete without
  asking the user first
- A secret, token or personal data being printed or stored by a script

## Reporting

Please **do not** open a public issue. Use
[GitHub private vulnerability reporting](https://github.com/saizul/oss-maintainer-skills/security/advisories/new)
with the affected skill, the impact and steps to reproduce.

You will get an answer within 5 working days. Fixes are released as soon as possible
and credited in the changelog unless you prefer otherwise.
