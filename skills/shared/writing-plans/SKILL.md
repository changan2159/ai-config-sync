---
name: writing-plans
description: Use when the user explicitly asks for a plan, or when a task is large enough that a short implementation plan materially improves execution and the overall workflow is already understood. Produce a concise, file-aware plan with verification steps and clear sequencing. For choosing between quick path, phase path, or parallelization strategy, use `project-orchestration` first.
---

# Planning Lite

Use this skill for substantial multi-step work. Keep the plan lean and executable.

## When To Plan

- The user asks for a plan or design first.
- The task spans multiple modules or systems.
- There are ordering constraints, migrations, or risky rollout concerns.

Skip a formal plan for obvious single-file or low-risk edits.

## Repo First

Before writing the plan, check the repository for constraints the user may not have mentioned explicitly.

- read the most relevant authority sources first
- prefer existing docs, code paths, tests, and configuration over assumptions
- if key terminology or ownership is unclear, use `clarify-with-repo-context` before locking the plan

Do not produce a polished plan around a guessed understanding of the system.

## Plan Requirements

- State the goal in one or two sentences.
- List the non-negotiable requirements that must not be silently dropped.
- State the acceptance criteria in observable terms when they are known.
- List the main workstreams in execution order.
- Call out the files or areas likely to change when known.
- Include the verification for each workstream.
- Note key assumptions, dependencies, and open risks.

## Acceptance Criteria

A good plan distinguishes between:

- implementation steps
- proof that the implementation works
- proof that it matches the user's requested outcome

If the request is underspecified, say what success currently means and what remains open. Do not hide missing acceptance criteria inside vague plan language.

## Scope Parity Check

Before finalizing the plan, check that the plan still matches the user's requested scope.

- Call out any requirement that is intentionally deferred or excluded.
- Do not silently shrink the requested behavior into an easier subset.
- If the safest implementation is narrower than the user's request, say so explicitly instead of pretending the narrower plan is equivalent.

If the requested behavior and the repo's current conventions appear to conflict, call out the conflict instead of writing a plan that quietly picks one side.

## Dependency And Wave Planning

When the task is large enough to benefit from parallel work, add a wave view in addition to the main execution order.

- Put only dependency-independent tasks in the same wave.
- Keep file and module ownership explicit for each parallel task.
- Prefer vertical slices over layer-based splits when the work crosses API, service, and test boundaries.
- Keep critical-path tasks serial when the next step depends on their result immediately.

Do not force a wave view for small plans. Use it only when it clarifies execution.

## Slice Selection

Prefer plans that deliver end-to-end slices of behavior.

- good: one API path or user workflow plus its service, data, and tests
- weaker: "controllers first, then services, then repositories, then tests"

Layer-based plans are acceptable when the task is truly infrastructural, but do not default to them for feature work.

## Granularity

- Prefer a small number of meaningful steps over a long checklist.
- Make each step outcome-oriented, not ceremonial.
- Include enough detail that another engineer could execute it without guessing.

Each step should answer:

- what changes
- where it changes
- how it will be verified

If a step has no concrete verification, it is probably not ready.

## Verification Design

Attach verification to each workstream, not only to the plan footer.

Prefer the smallest convincing check:

- focused test update
- targeted build or lint scope
- endpoint or UI behavior check
- migration generation and application check

For risky tasks, include both narrow verification and one broader end-to-end confirmation.

## Preferred Shape

```markdown
# <Task Name>

## Goal
<What success looks like>

## Non-Negotiables
- <behavior, requirement, or constraint that cannot be lost>

## Acceptance Criteria
- <observable outcome that proves success>

## Plan
1. <Step> - files/areas: <paths>; verify: <check>
2. <Step> - files/areas: <paths>; verify: <check>
3. <Step> - files/areas: <paths>; verify: <check>

## Waves
- Wave 1: <parallel-safe tasks or "not needed">
- Wave 2: <dependent follow-up tasks>

## Risks
- <important risk or dependency>
```

Adapt the format when the user wants something else, but keep the same substance.
