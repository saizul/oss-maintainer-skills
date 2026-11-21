# Reply templates

Start every reply with a personal first line that shows you read the issue. Replace the
`<...>` parts. Keep replies short; link docs instead of repeating them.

## Thanks, confirmed

> Thanks for the clear report, @<user>! I can reproduce this on <version> with
> <minimal steps>. It looks like <short cause if known>. I've labeled it `confirmed`;
> a fix will land in the next patch release. <If suitable: "If you'd like to send a PR,
> the change is probably in `<file>`, and I'm happy to help.">

## Needs reproduction (`needs-repro`)

> Thanks for reporting this, @<user>. I couldn't reproduce it yet. Could you add:
>
> - the version (`<tool> --version`) and your OS / runtime version
> - the exact command or the smallest code sample that fails
> - what you expected and what happened instead (full error output)
>
> I'll keep this open for 14 days; if we can't reproduce it by then I'll close it, and
> you can reopen any time with the details.

## Needs info, final nudge

> Hi @<user>, just checking in: are you still seeing this? Without the details above I
> can't move forward, so I'll close this in a week. Feel free to reopen with more info.

## Closing: no response

> Closing since we couldn't reproduce this and haven't heard back. If it still happens
> on the latest version, please reopen with the requested details. Thanks!

## Duplicate

> Thanks, @<user>! This is the same problem as #<number>, so I'm closing this one to
> keep the discussion in one place. Please add a 👍 or any new details there.

## Question, not a bug

> Good question! <Short answer or link to docs.> I'm moving this to Discussions
> (<link>) so others can find it; issues are for bugs and feature requests.

## Feature request: accepted / help wanted

> Thanks for the idea, @<user>. This fits the project and I've labeled it
> `help wanted`. Rough plan: <1-3 bullets>. Anyone is welcome to pick it up; comment
> here first so we can agree on the approach.

## Feature request: declined

> Thanks for taking the time to write this up, @<user>. I'm going to decline it
> because <reason: scope, maintenance cost, better solved by X>. <Alternative:
> plugin, wrapper, other tool>. I know that's not the answer you hoped for; I want to
> keep the project focused enough to maintain well.

## Stale

> This issue has had no activity for <N> days. Is it still relevant on the latest
> version? If so, please comment and it will stay open; otherwise it will be closed in
> 14 days. Thanks for your patience.

## Security report posted publicly

> Thanks for reporting this, @<user>. Because it may be a security issue, I've hidden
> the details here. Please send them through private vulnerability reporting:
> https://github.com/<owner>/<repo>/security/advisories/new and we'll follow up there.

(Edit or hide the original comment with the maintainer tools, and do not repeat the
details in your reply.)
