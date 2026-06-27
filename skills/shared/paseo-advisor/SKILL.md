---
name: paseo-advisor
description: Use when a task needs a second opinion through Paseo without transferring ownership of the implementation. Prefer this for read-only cross-review, architecture judgment, risk checks, and “did I miss anything” style validation after a plan or patch exists.
---

# Paseo Advisor

Use this skill to request a read-only second opinion from another agent through Paseo.

The advisor does analysis only. It does not own the implementation. The current agent remains responsible for judgment and follow-through.

Read `paseo` first for the full command surface when possible.
If this skill is invoked directly, keep these commands in mind:

```bash
paseo run --provider <provider> "<advisor prompt>"
paseo run --provider <provider> --output-schema '<schema>' "<advisor prompt>"
paseo wait <id-or-name>
paseo logs <id-or-name> --tail 40
```

## When To Use

Use this skill when:

- you want a second opinion before or after implementation
- you need cross-review on a diff, plan, or risky decision
- you suspect blind spots, tunnel vision, or under-verified behavior
- you want another provider to evaluate maintainability, UX risk, or regression risk

Do not use it when:

- the task is trivial and independent review would cost more than it saves
- the advisory context is too incomplete for a useful judgment
- you actually need another agent to implement, not advise

## Best Uses

- review a multi-file patch before final delivery
- check whether a plan misses migration or rollout risks
- validate whether tests are sufficient
- ask for a product or UX risk pass on a proposed UI change
- get a contrasting provider’s read on a bug hypothesis

## Advisor Prompt Rules

An advisor prompt should:

- be explicitly read-only
- provide the intended behavior and current state
- ask for findings or judgment, not implementation
- request concise, prioritized output

Good prompt shape:

```text
Review the current plan/diff/task as an advisor only.
Do not edit files.
Focus on: <correctness|regression|maintainability|security|UX risk>
Context: <brief context>
Return: prioritized findings, missing verification, and any major blind spots.
```

## Default Command Shape

```bash
paseo run --provider claude "<advisor prompt>"
```

Use `--output-schema` when you need a strict pass/fail or structured judgment.

## Output Expectations

When using this skill, the agent should make explicit:

- why advisory review is worthwhile
- what lens the advisor should use
- that the advisor is read-only
- how the advice will influence the next step
