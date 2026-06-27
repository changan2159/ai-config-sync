---
name: using-superpowers
description: Use at the start of a conversation to set the default operating style for skill usage. Prefer simple, surgical work, surface assumptions when they matter, and use narrower skills when the task clearly fits them or they materially reduce error.
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

## Default Routing

Use another skill when one of these is true:

- the user explicitly names the skill
- the task clearly matches a specialized domain or framework skill
- the repository task is materially underspecified, terminology-heavy, or likely to drift without context alignment; use `clarify-with-repo-context`
- the main need is repository retrieval, ownership discovery, or finding the smallest complete file set; use `fast-codebase-retrieval`
- the task depends on definitions, references, implementations, call chains, or dependency wiring; use `serena-workflow` or a narrower Serena-based skill such as `csharp-symbolic-workflow`
- the task is an unclear or mixed optimization, improvement, or refactor request; use `code-optimization`
- the task involves non-trivial code changes or review where reuse, abstraction boundaries, duplicate logic, or file maintainability matter; pair the domain skill with `code-maintainability`
- the main risk is brownfield ownership entropy, file bloat, shallow wrappers, or duplicated orchestration; add `architecture-deepening`
- the task is product-style frontend implementation, redesign, polish, or responsive fixing; use `frontend-design` and pair with `frontend-ui-engineering` when component logic or shared UI patterns are substantial
- the task is Java or Spring Boot feature work, debugging, schema changes, security, testing, or dependency management; use `java-spring-workflow`
- the first problem is choosing a workflow shape for substantial multi-step work; use `project-orchestration`
- the main decision is whether clearly independent workstreams are safe to split; use `parallel-execution`
- provider-backed contrast or bounded advisory orchestration would materially reduce risk and `paseo` is available; use `paseo-advisor`, `paseo-committee`, `paseo-handoff`, or `paseo-loop` as appropriate
- the task is clearly a phased migration or compatibility-sensitive refactor; use `large-refactor`
- the issue is a failing build, test, or unclear behavior; use `systematic-debugging`
- the user wants commit-message drafting or staged change review; use `git-commit`
- the task is addressing GitHub PR review comments or fixing failing GitHub Actions checks; use `gh-address-comments` or `gh-fix-ci`
- the user mainly wants a plan; use `writing-plans`

For tiny or string-driven work, stay direct: use targeted file inspection or text search for config keys, route fragments, SQL, logs, JSON or YAML fields, docs, templates, or tiny edits in already-known files. When Serena is available and the task is clearly brownfield structure work rather than a tiny local edit, prefer Serena-backed navigation proactively; escalate from direct search once the task stops being local and turns into structure tracing.

Do not invoke skills by reflex for every message. If no specialized skill clearly helps, proceed directly.

## Optimization Requests

When the user asks to optimize, improve, or refactor code:

- classify the primary axis as `maintainability`, `architecture`, `performance`, `reliability`, or `developer-experience`
- if the axis would materially change the solution, clarify first; otherwise state the assumed axis briefly
- if the axis is unclear or mixed, start with `code-optimization`; if it is already clearly maintainability-focused, go directly to `code-maintainability`
- preserve external behavior unless the user explicitly asks for a behavior change
- prefer the smallest high-leverage change instead of a broad rewrite

## Assumptions And Ambiguity

- State assumptions when they affect the solution.
- If there are multiple plausible interpretations with materially different outcomes, ask or present the tradeoff.
- If a simpler approach is better than the implied one, say so and use it unless the user objects.

## Simplicity And Scope

- Do not add abstractions, configuration, or features that were not requested.
- Match the existing code and workflow unless there is a concrete reason to diverge.
- Before adding new code, do a quick reuse scan for existing owners, helpers, fixtures, and framework features that already represent the concept.
- Look first at nearby files, existing symbols, shared folders, tests, and framework built-ins before creating a new helper, component, service, hook, DTO, or module.
- Prefer extending or composing an existing owner when it already represents the concept; create a new abstraction only when reuse would blur ownership, add awkward flags, or couple unrelated flows.
- Extract repeated logic when it is the same concept and likely to change together; avoid broad shared abstractions for coincidental similarity.
- Keep a rule-of-three bias before introducing broad shared abstractions unless the existing architecture already clearly requires one.
- Touch only the files and lines needed for the request. Clean up unused code when your own change created it. Mention unrelated issues you notice, but do not fix them unless asked.

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
