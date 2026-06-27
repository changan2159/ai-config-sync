---
name: paseo-handoff
description: Use when work should be handed to another agent through Paseo with a bounded scope, clear ownership, and a self-contained briefing. Prefer this for delegated implementation slices, independent review passes, and non-critical-path follow-up tasks once the write boundary is stable.
---

# Paseo Handoff

Use this skill to hand a bounded task to another agent through the `paseo` CLI.

This is the default shared delegation path when another agent should own a concrete slice of work and the current agent should either continue on the main thread or wait for the result.

Read `paseo` first for the command surface and safety rules.

## When To Use

Use this skill when:

- a subtask has a clear outcome and bounded scope
- another provider is a better fit for the slice
- you want an independent review or implementation pass
- the current task can be decomposed without overlapping writes

Do not use it when:

- the target files or interface are still unstable
- the request is too vague to hand off safely
- the delegated task is the immediate blocking task and is faster to do locally

## Good Fits

- hand off a review pass after implementation is locally complete
- hand off a non-overlapping implementation slice
- ask another provider to validate edge cases or test gaps
- send a frontend polish slice, docs slice, or verifier-only task while keeping the mainline local

## Briefing Requirements

Every handoff prompt should include:

- the concrete task
- the allowed scope
- the forbidden scope
- relevant files or modules
- known context or attempted paths
- the required output format
- whether edits are allowed
- the acceptance criteria

## Default Handoff Shape

Use a prompt shape like:

```text
Task: <desired outcome>
Context: <current state and why this is delegated>
Allowed scope: <files/modules/commands>
Forbidden scope: <areas not to touch>
Verification: <tests, review criteria, or output schema>
Return: <summary, findings, patch intent, or structured JSON>
```

## Provider Selection Heuristics

- use a strong reviewer or planner for analysis-heavy read-only handoffs
- use a strong implementer for bounded code changes
- use the same provider family only when the value is execution isolation or background progress rather than contrast

If no provider is explicitly required, choose the most suitable one for the task and explain the choice briefly.

## Worktree Rule

Use `--worktree` when:

- the delegated task may touch many files
- you want strong isolation from the current branch state
- you may compare or discard the result independently

Avoid worktrees for tiny review-only tasks.

## Review-Only Handoff

For cross-review, keep the worker read-only.

Ask it to:

- inspect the diff or named files
- identify concrete risks
- avoid editing or rewriting the current branch
- return findings in priority order

## Implementation Handoff

For delegated implementation:

- keep the file boundary explicit
- tell the worker not to broaden scope
- state whether tests should be run
- specify whether the main agent will integrate manually or just inspect logs/results

## Example Command Shapes

```bash
paseo run --detach --name review-pass --provider claude "<briefing>"
paseo run --provider codex --worktree feature-x "<briefing>"
paseo send review-pass "Also verify migration rollback behavior."
paseo wait review-pass
paseo logs review-pass --tail 40
```

## Output Expectations

When using this skill, the agent should state:

- why delegation is warranted
- what the delegated agent owns
- which provider is chosen and why
- whether the task is read-only or may edit
- whether the main thread will wait or continue
