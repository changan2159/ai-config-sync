---
name: paseo-committee
description: Use when the task is stuck, ambiguous, or structurally risky enough to justify two contrasting read-only analyses before implementation. Prefer this for root-cause analysis, migration planning, difficult tradeoffs, and “step back and rethink” moments.
---

# Paseo Committee

Use this skill when one advisor is not enough and the main need is better thinking, not immediate editing.

A committee is a small multi-agent analysis pass, typically two high-reasoning agents with contrasting perspectives. They analyze the problem read-only. The current agent synthesizes the result and decides what to implement.

Read `paseo` first for the shared command surface.

## When To Use

Use this skill when:

- the task is stuck or looping without clarity
- there is meaningful ambiguity in architecture or root cause
- the cost of a wrong plan is high
- you want two contrasting analyses before committing to implementation

Do not use it when:

- the issue is already well understood
- a single focused advisor is enough
- the problem is too small to justify the overhead

## Committee Rules

Committee members should:

- stay read-only
- analyze the same problem from slightly different angles
- return findings, hypotheses, tradeoffs, and recommended next steps
- avoid editing, deleting, or creating files

The orchestrating agent should:

- compare the analyses
- identify overlap and disagreement
- choose a plan
- own implementation and verification

## Good Fits

- why a bug keeps recurring despite local fixes
- migration strategy across shared contracts
- performance or scalability diagnosis with multiple plausible causes
- choosing between two architectural seams

## Prompt Shape

```text
Analyze this problem as a read-only committee member.
Do not edit files.
Focus on root cause, risks, tradeoffs, and recommended next steps.
Context: <problem summary>
Return: concise findings and a recommended plan.
```

## Output Expectations

When using this skill, the agent should state:

- why a committee is justified
- that members are analysis-only
- what contrasting lenses are desired
- how the synthesis will be turned into a concrete next step
