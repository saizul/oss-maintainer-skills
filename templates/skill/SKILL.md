---
name: your-skill-name
description: One or two sentences on WHAT the skill does (concrete outputs, tools, file names) followed by WHEN to use it. Use when the user asks to ..., mentions ..., or is about to .... Keep it under 1024 characters and include the words people actually type.
license: MIT
metadata:
  author: Your Name
  version: "0.1.0"
---

# Skill title

One short paragraph: the goal of the skill and the principle behind it.

## When to use

- Typical request, phrased the way a user would say it
- Situation where this skill should kick in

## When not to use

- Neighbouring task that another skill or tool handles better
- Anything unsafe or out of scope

## Workflow

1. **Gather facts.** What to read first (files, commands). Never invent facts.

2. **Run the helper** (`scripts/` is relative to this skill's directory):

   ```bash
   python3 scripts/your_script.py --help
   python3 scripts/your_script.py . --json
   ```

3. **Decide.** Decision points and what to ask the user.

4. **Act.** The exact steps. Ask before anything that posts, publishes, pushes or deletes.

5. **Verify.** How to check the result.

## Output

- What the user gets at the end (files, a report, drafts)
- What is left for the user to do
