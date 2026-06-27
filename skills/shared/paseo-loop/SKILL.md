---
name: paseo-loop
description: Use when a worker-verifier loop through Paseo is a better fit than a single delegation. Prefer this for repeated implement-and-check cycles with clear stop conditions, such as fixing tests until green, iterating until a review criterion is met, or babysitting a bounded workflow.
---

# Paseo Loop

Use this skill when the right workflow is not “delegate once”, but “repeat until a clear exit condition is met”.

A Paseo loop is a worker/verifier cycle. A worker attempts the task. A verifier checks whether the acceptance criteria are met. Repeat until success or a defined limit is reached.

Read `paseo` first for command surface details.

## When To Use

Use this skill when:

- the task can be judged by a clear verification signal
- retries may be needed
- you want bounded autonomy rather than open-ended delegation
- a shell check, targeted test, or structured reviewer can determine completion

Do not use it when:

- the acceptance criteria are vague
- each iteration would change architecture or scope significantly
- the worker and verifier would both modify the same files

## Good Exit Signals

- a targeted test file passes
- a linter or typecheck command succeeds
- a structured verifier returns `criteria_met: true`
- a focused reviewer finds no blocking issues

## Required Limits

Always set at least one bound:

- max iterations
- max total time
- both when the task is expensive or failure-prone

Do not create indefinite loops.

## Worker/Verifier Split

Keep roles explicit:

- worker: may edit and run allowed verification commands
- verifier: ideally read-only, judges whether the output satisfies the requested condition

Use a shell verifier when the result is deterministic.
Use an advisor/reviewer verifier when the result is qualitative.
Use both when useful.

## Prompt Rules

The loop definition should include:

- the worker goal
- the verifier condition
- iteration and time limits
- whether worktrees or isolated branches are required
- what to do on final failure

## Example Pattern

```bash
while true; do
  paseo run --provider codex "make the targeted test pass without broadening scope" >/dev/null
  verdict=$(paseo run --provider claude --output-schema '{"type":"object","properties":{"criteria_met":{"type":"boolean"}},"required":["criteria_met"],"additionalProperties":false}' "Review whether the current change fully satisfies the acceptance criteria and reply only in schema form.")
  # stop when criteria_met is true or limits are hit
  break
done
```

## Output Expectations

When using this skill, the agent should state:

- the worker task
- the verifier signal
- the loop bounds
- why a loop is better than a one-shot delegation
