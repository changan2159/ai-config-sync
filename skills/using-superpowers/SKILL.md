---
name: using-superpowers
description: Use at the start of a conversation to set the default operating style for skill usage. Prefer simple, surgical work, surface assumptions when they matter, and use other skills when the task clearly matches them.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

# Working Style

Use this skill as the lightweight top-level policy for the rest of the session.

## Priorities

1. Follow direct user instructions and repository instructions first.
2. Prefer the simplest approach that solves the actual request.
3. Make narrow, task-traceable changes.
4. Verify outcomes with concrete checks.

## Skill Usage

Use another skill when one of these is true:
- The user explicitly names the skill.
- The task clearly matches a specialized domain such as browser automation, framework-specific work, CI debugging, or OpenAI product guidance.
- The user is asking about the current repository and the main need is to find where behavior lives, which files are related, how code paths connect, or what the smallest complete file set is; default to `fast-codebase-retrieval` before broader implementation work.
- The task requires brownfield code understanding, dependency wiring, cross-file behavior tracing, or symbol-aware structure discovery; default to `serena-workflow` or a narrower Serena-based skill such as `csharp-symbolic-workflow`.
- The task involves non-trivial code changes, refactoring, or review where reuse, abstraction boundaries, duplicate logic, or file maintainability matter; pair the domain skill with `code-maintainability`.
- The task is risky enough that a structured workflow materially reduces mistakes.

When Serena tooling is available for the active workspace, prefer Serena-backed navigation before broad text search or full-file reads for existing-code analysis. Do not wait for the user to ask for Serena explicitly.

Use this task-shape rule:

- Default to `fast-codebase-retrieval` when the question is about the current repo and success depends on finding the right files before editing or explaining behavior.
- Default to Serena-first when the task depends on definitions, references, implementations, call chains, dependency wiring, or cross-project impact.
- Default to direct text search or targeted file inspection when the task is mainly about config keys, route fragments, SQL, logs, JSON or YAML fields, docs, templates, or a tiny edit in already-known files.
- Start direct and escalate to Serena if the task stops being local and turns into structure tracing.
- Do not force Serena onto trivial tasks where symbol-aware setup would cost more than it saves.

For substantial multi-step work, prefer `project-orchestration` as the thin top-level router before invoking narrower skills.
If the task may benefit from multiple roles or parallel waves, consider `parallel-execution` after choosing the orchestration path.
If the task is obviously only a plan request, go straight to `writing-plans`. If it is obviously a phased migration or compatibility-sensitive refactor, go straight to `large-refactor`.
If the problem is clearly a localized test-harness or validation setup mismatch, stay in direct execution or `systematic-debugging` instead of escalating prematurely.

Do not invoke skills by reflex for every message. If no specialized skill clearly helps, proceed directly.

## Assumptions And Ambiguity

- State assumptions when they affect the solution.
- If there are multiple plausible interpretations with materially different outcomes, ask or present the tradeoff.
- If a simpler approach is better than the implied one, say so and use it unless the user objects.

## Simplicity

- Do not add abstractions, configuration, or features that were not requested.
- Match the existing code and workflow unless there is a concrete reason to diverge.
- If a long solution can be made much shorter without losing correctness, shorten it.

## Reuse First

- Run a quick reuse scan before adding a new component, function, method, helper, service, hook, endpoint, DTO, query, test fixture, public type, package, or top-level module.
- Inspect nearby files, existing symbols, shared folders, framework built-ins, dependencies, and tests for similar behavior, call patterns, data mappings, validation rules, and established conventions.
- Prefer extending or composing existing services, DTOs, serializers, UI primitives, hooks, utilities, test builders, and module contracts when they fit.
- Keep touched files cohesive and scannable. If a change would add a second unrelated responsibility to a file, split or move the new code to the narrowest existing boundary.
- Extract repeated calls or duplicated logic when the repeated code represents the same concept and is likely to change together; avoid broad abstractions for coincidental similarity.
- Create a new abstraction only when reuse is clearly worse or incompatible; keep the reason visible in the implementation note or final response.
- Apply a rule-of-three bias before introducing broad shared abstractions unless the existing architecture already requires one.

## Surgical Changes

- Touch only the files and lines needed for the request.
- Clean up unused code only when your own change created it.
- Mention unrelated issues you notice, but do not fix them unless asked.

## Verification

- Define what success looks like before finishing.
- Run the smallest useful verification for the task.
- If you could not verify something important, say so plainly.

## Escalation Path

Escalate from direct execution to orchestration when one or more are true:

- the task spans multiple modules
- execution ordering matters
- the work may continue across sessions
- safe parallelization depends on explicit ownership
- delivery risk is high enough that layered verification is needed

Use the lightest workflow that still controls the risk.
