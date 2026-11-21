---
name: project-launch
description: Plans and drafts the public launch of an open-source project - a readiness checklist, where to announce (Show HN, relevant subreddits, dev.to, Lobsters, newsletters, awesome lists, social media) and how each community's rules work, plus a script that drafts a Show HN title and first comment, a Reddit post, a dev.to article and a short social post and lints titles for length, hype and rule violations. Use when the user wants to launch, announce, promote or get the first users or stars for a project, or asks how to post on Hacker News, Reddit or dev.to.
license: MIT
metadata:
  author: Saizul Amin
  version: "0.1.0"
---

# Project launch

A launch turns a finished project into a used one. Most launches fail before posting:
the README does not explain the project, or the first command does not work. Fix that,
then post in a few places where the right people are, and be there to answer.

## When to use

- "How do I launch / announce / promote my project?"
- Drafting a Show HN, Reddit or dev.to post
- Planning a launch week, or a release announcement for a big version

## When not to use

- Paid advertising, growth hacking, or buying stars and votes: never do this; it gets
  projects banned and destroys trust.
- Posting on the user's behalf: this skill drafts. **The user posts from their own
  accounts.** Do not submit, post or message anyone.

## Workflow

1. **Readiness.** Run the `repo-health-check` skill (aim for 80+) and the
   `readme-writer` lint. Walk through the [launch checklist](references/checklist.md)
   with the user. Do not launch with a broken quick start.

2. **Pick channels** with the user from [channels.md](references/channels.md):
   one or two big ones (Show HN, the best-fitting subreddit) plus the niche ones where
   the target users actually are. Read each community's current rules before posting;
   they change.

3. **Draft posts** (`scripts/` is relative to this skill):

   ```bash
   python3 scripts/launch_drafts.py drafts --name NAME --url https://github.com/OWNER/REPO --readme README.md --tags python,cli,opensource
   python3 scripts/launch_drafts.py drafts --name NAME --url URL --pitch "One-sentence pitch." --json
   python3 scripts/launch_drafts.py lint-title "Show HN: NAME – what it does" --site hn
   ```

   Fill every `[FILL IN]` with the user's real story: why they built it, what is hard
   about it, what it does not do yet. Specific beats polished. Never invent numbers,
   users or testimonials. Templates and examples are in [posts.md](references/posts.md).

4. **Schedule.** Space the posts over several days rather than everywhere at once, so
   the user can answer every comment. Avoid launching right before a holiday or the
   user's own unavailable hours.

5. **During the launch.** Remind the user to: reply to every comment quickly and
   without defensiveness, fix small bugs live and say so, collect feature requests as
   issues, and thank people. Never ask friends to upvote; HN and Reddit detect and
   penalize voting rings.

6. **After.** Write down what worked, turn feedback into issues (label
   `good first issue` where suitable), and post a short follow-up with a real update
   weeks later rather than reposting.

## Output

- The readiness checklist with pass/fail per item.
- A channel plan (where, when, which draft).
- Final drafts per channel, with title lint results and the remaining `[FILL IN]` items.

## Title lint rules

| Site | Rules checked |
| --- | --- |
| hn | starts with `Show HN: `, 80 characters max, no `!`, no emoji |
| reddit | 300 characters max |
| devto | 128 characters max (the script's own limit to keep titles readable) |
| all | hype words (best, fastest, revolutionary...), capitalized shouting, asking for votes or stars |

Exit code 1 when a title has errors, so drafts can be checked in a loop.
