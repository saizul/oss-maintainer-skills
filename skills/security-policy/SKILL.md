---
name: security-policy
description: Sets up vulnerability handling for an open-source repository - writes SECURITY.md with supported versions and GitHub private vulnerability reporting, generates a .github/dependabot.yml covering every detected ecosystem (pip, npm, composer, github-actions, docker, gomod, cargo, bundler, maven, gradle, nuget) with grouped updates, checks coverage, and guides the maintainer through handling a report and publishing an advisory. Use when the user asks for a security policy, SECURITY.md, Dependabot, private reporting, or what to do after receiving a vulnerability report.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Security policy

Researchers need to know where to report privately, users need to know which versions
get fixes, and dependencies need to stay patched without manual work.

## When to use

- "Add a SECURITY.md" / "set up Dependabot" / "enable private vulnerability reporting"
- The repo-health-check skill reported missing `security` or `dependency-updates`
- A vulnerability report arrived and the maintainer needs a process

## When not to use

- Auditing the code itself for vulnerabilities (use a scanner or a security review).
- Renovate users: keep Renovate; the `check` command accepts its config.

## Workflow

1. **Check** the current state (`scripts/` is relative to this skill):

   ```bash
   python3 scripts/gen_security.py check .
   python3 scripts/gen_security.py ecosystems .
   ```

2. **SECURITY.md.** Ask which versions get security fixes (often "latest minor" for
   small projects) and the response time the maintainer can really keep.

   ```bash
   python3 scripts/gen_security.py security-md --repo OWNER/NAME --supported "1.4.x" --response-days 5
   python3 scripts/gen_security.py security-md --repo OWNER/NAME --write    # never overwrites without --force
   ```

   Add project-specific "what counts as a vulnerability" bullets (the generator leaves
   a generic scope); good examples are in [handling.md](references/handling.md).
   Do not add a personal email address unless the user gives one for this purpose.

3. **Dependabot.**

   ```bash
   python3 scripts/gen_security.py dependabot .              # preview
   python3 scripts/gen_security.py dependabot . --write      # .github/dependabot.yml
   python3 scripts/gen_security.py dependabot . --interval monthly --no-groups
   ```

   It includes `github-actions` whenever workflows exist, groups minor and patch updates
   into one PR per ecosystem, labels PRs `dependencies` and uses `deps:`/`ci:` commit
   prefixes. Make sure the `dependencies` label exists (`contributor-onboarding` skill).

4. **Repository settings** the maintainer must switch on (the script cannot): in
   Settings > Security (Advanced Security / Code security, depending on the plan):
   private vulnerability reporting, Dependabot alerts, Dependabot security updates,
   secret scanning and push protection where available. Give the user this list.

5. **Re-run `check`** until it prints `ok`.

## Handling a report

Follow [handling.md](references/handling.md): acknowledge, reproduce privately,
create a draft security advisory, fix in a private fork, request a CVE, release, publish.
Never discuss an unfixed vulnerability in a public issue, PR or commit message.

## Output

- SECURITY.md and `.github/dependabot.yml` (written or shown).
- The `check` result and the list of settings the user must enable by hand.
