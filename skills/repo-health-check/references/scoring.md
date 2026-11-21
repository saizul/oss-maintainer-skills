# Why each check matters

Use these one-liners when you explain a failed check to the user.

- **README (25 points across two checks).** It is the landing page. Visitors decide in
  seconds whether the project solves their problem; without install and usage sections
  they leave.
- **Badges.** A green CI badge and a version badge signal that the project is maintained
  and released. They are cheap trust signals.
- **LICENSE.** Code without a license is "all rights reserved" by default. Companies and
  careful individuals cannot use or contribute to it.
- **CONTRIBUTING.** Tells a newcomer how to set up, test and submit. Every question it
  answers is one fewer barrier to a first pull request.
- **CODE_OF_CONDUCT.** Sets expectations and gives people a private way to report
  problems. GitHub shows it in the community profile.
- **SECURITY.md.** Tells researchers where to report privately instead of in a public
  issue. GitHub links it from the Security tab.
- **Issue templates.** Structured bug reports (version, steps, expected vs actual) cut
  triage time dramatically.
- **PR template.** A checklist (tests, docs, changelog) that contributors fill in before
  review.
- **CI.** Contributors need fast, automatic feedback; maintainers need to trust a PR
  before reading it.
- **Tests.** Without them nobody, including you, can change code with confidence.
- **CHANGELOG.** Users upgrading need to know what changed and what breaks.
- **.gitignore.** Keeps build output, virtualenvs and secrets out of commits.
- **Dependency updates.** Dependabot or Renovate keeps dependencies and Actions current
  and surfaces security fixes as PRs.

## What the script does not check

- Whether the content is good: read the README yourself.
- GitHub settings: description, topics, website link, social preview image, Discussions,
  private vulnerability reporting, branch protection. Remind the user to set these in the
  repository settings; they matter for discovery.
