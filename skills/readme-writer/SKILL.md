---
name: readme-writer
description: Writes or rewrites a project README that converts visitors into users and contributors - one-line pitch, badges, a 60-second quick start, real examples, features, FAQ, contributing and license - and lints it for missing sections, broken relative links, missing alt text and a late first code block. Use when the user asks to write, improve, review or restructure a README, says nobody understands or stars the project, or is preparing an open-source launch.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# README writer

A README has one job: get a visitor from "what is this?" to a working first command
in under a minute, then show them how to go further and how to help.

## When to use

- Writing a README for a new project, or rewriting a thin or rambling one
- Reviewing a README before a launch or a 1.0 release
- The user says the project gets visits but no stars, installs or contributors

## When not to use

- API reference documentation (generate it from code; link it from the README)
- Long tutorials or architecture docs: put them in `docs/` and link them

## Workflow

1. **Gather facts before writing.** Read the manifest (`pyproject.toml`, `package.json`,
   `composer.json`, `Cargo.toml`...), the CLI `--help` or main entry point, existing docs,
   and the license. Find the real install command and a real example. Never invent
   flags, outputs, benchmarks or features.

2. **Ask the user only what the code cannot tell you:** who the project is for, the one
   problem it solves, and why it is better than the obvious alternative. If they are not
   available, write a neutral pitch from the code and mark it for review.

3. **Lint the current README** (if there is one). `scripts/` is relative to this skill:

   ```bash
   python3 scripts/readme_lint.py README.md
   python3 scripts/readme_lint.py README.md --json --strict
   ```

4. **Write using the structure** in [structure.md](references/structure.md), starting
   from [the template](assets/README.template.md). Order matters:
   title + badges, pitch, (demo image), quick start, features, usage/examples,
   configuration, FAQ, roadmap, contributing, license.

5. **Apply the writing rules:**
   - Pitch: one sentence, under 200 characters, no hype words. Pattern:
     "`<name>` is a `<category>` that `<does X>` for `<audience>`, `<key differentiator>`."
   - First code block above line 60. Every command must be copy-pasteable and real.
   - Show output after commands where it helps (`# => ...` or a separate block).
   - Use tables for options and comparisons, lists for features (benefit first).
   - Link, don't paste: long docs, changelogs and API references go elsewhere.
   - Every image gets alt text; prefer an SVG or a short GIF of the main flow.

6. **Badges.** Use only badges that are true and maintained, in this order: CI status,
   latest version (PyPI/npm/Packagist/release), downloads (optional), license.
   Examples in [structure.md](references/structure.md#badges).

7. **Re-lint** until there are no errors. Resolve warnings or tell the user why not.

8. **Check the links** the linter cannot: absolute URLs and anchors. Click-test or
   explain which were not verified.

## Output

- The new or updated README.md (show a diff summary for rewrites).
- The final lint result.
- A short list of facts you could not verify and placeholders the user must fill
  (demo GIF, screenshots, benchmark numbers).

## Lint rules

| Rule | Level | Meaning |
| --- | --- | --- |
| title | error/warning | exactly one H1 |
| pitch | error/warning | a short first paragraph under the title |
| badges | warning | no badge found |
| install | error/warning | install (or quick start) section, with a code block |
| quickstart | error/warning | usage, quick start or example section, with code |
| code | error | no code block at all |
| scroll | warning | first code block after `--max-scroll` lines (default 60) |
| contributing, license | warning | missing section |
| faq, toc | info | suggested |
| alt-text | warning | image without alt text |
| broken-link | error | relative link to a missing file, or an empty link |
| placeholder | warning | TODO, TBD or lorem ipsum left in |

Exit 1 on errors (and on warnings with `--strict`).
