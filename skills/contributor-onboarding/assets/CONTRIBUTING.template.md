# Contributing to PROJECT

Thanks for helping! Bug reports, docs, tests and code are all welcome, and you do not
need to be an expert to start.

## Ways to contribute

| Time | Idea |
| --- | --- |
| 10 minutes | Fix a typo, improve an error message, answer a question in Discussions |
| 1 hour | Pick a [good first issue](https://github.com/OWNER/REPO/labels/good%20first%20issue), add a test |
| Longer | A feature from the roadmap (open an issue first so we can agree on the design) |

Comment on an issue before you start so nobody duplicates your work.

## Development setup

Requirements: RUNTIME VERSION, git.

```bash
git clone https://github.com/OWNER/REPO.git
cd REPO
SETUP-COMMAND
```

## Running tests and checks

```bash
TEST-COMMAND
LINT-COMMAND
FORMAT-COMMAND
```

CI runs the same commands on every pull request.

## Coding style

- STYLE RULES (formatter, line length, naming).
- Add or update tests for every behaviour change.
- Keep pull requests focused: one change per PR.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/):
`feat: add --json output`, `fix(parser): handle empty files`, `docs: add FAQ entry`.
A `!` or a `BREAKING CHANGE:` footer marks breaking changes. Release notes are
generated from these messages.

## Pull request process

1. Fork the repository and create a branch: `git checkout -b fix/short-description`.
2. Make your change with tests, and run the checks above.
3. Update the docs and `CHANGELOG.md` (under "Unreleased") if users will notice.
4. Open a pull request and fill in the template. Link the issue (`Closes #123`).
5. A maintainer reviews within RESPONSE TIME. We may suggest changes; that is normal.

## Reporting bugs and requesting features

Use the [issue forms](https://github.com/OWNER/REPO/issues/new/choose). For security
problems, follow [SECURITY.md](SECURITY.md) and do not open a public issue.

## Code of conduct

Everyone taking part agrees to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
