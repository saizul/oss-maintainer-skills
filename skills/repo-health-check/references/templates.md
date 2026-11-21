# Issue and pull request templates

Copy these into the repository and adapt the wording to the project. Issue forms
(`.yml`) render as structured forms on GitHub.

## .github/ISSUE_TEMPLATE/bug_report.yml

```yaml
name: Bug report
description: Something does not work as documented
labels: ["bug", "needs-triage"]
body:
  - type: markdown
    attributes:
      value: Thanks for reporting! Please search existing issues first. Never paste secrets.
  - type: input
    id: version
    attributes:
      label: Version
      description: Output of `<tool> --version`, or the package version
    validations:
      required: true
  - type: textarea
    id: steps
    attributes:
      label: Steps to reproduce
      description: The smallest set of commands or code that shows the problem.
      placeholder: |
        1. ...
        2. ...
    validations:
      required: true
  - type: textarea
    id: expected
    attributes:
      label: Expected behaviour
    validations:
      required: true
  - type: textarea
    id: actual
    attributes:
      label: Actual behaviour
      description: Include the full error message or log output.
      render: shell
    validations:
      required: true
  - type: input
    id: environment
    attributes:
      label: Environment
      placeholder: "OS, runtime version (Python 3.13 / Node 24 / PHP 8.4)"
```

## .github/ISSUE_TEMPLATE/feature_request.yml

```yaml
name: Feature request
description: Suggest an idea or improvement
labels: ["enhancement", "needs-triage"]
body:
  - type: textarea
    id: problem
    attributes:
      label: What problem would this solve?
      description: Describe the use case, not only the solution.
    validations:
      required: true
  - type: textarea
    id: proposal
    attributes:
      label: Proposed solution
  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives you considered
  - type: checkboxes
    id: contribute
    attributes:
      label: Contribution
      options:
        - label: I would like to work on this
```

## .github/ISSUE_TEMPLATE/config.yml

```yaml
blank_issues_enabled: false
contact_links:
  - name: Question
    url: https://github.com/OWNER/REPO/discussions
    about: Ask and answer questions in Discussions.
  - name: Security issue
    url: https://github.com/OWNER/REPO/security/advisories/new
    about: Report vulnerabilities privately.
```

## .github/pull_request_template.md

```markdown
## What does this change?

<!-- One or two sentences. Link the issue: "Closes #123". -->

## Checklist

- [ ] Tests added or updated, and they pass locally
- [ ] Docs / README updated if behaviour changed
- [ ] CHANGELOG.md updated under "Unreleased"
- [ ] Commits follow Conventional Commits (feat:, fix:, docs: ...)
```
