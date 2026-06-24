---
name: project-orchestration
description: Use when you first need to choose the right workflow for substantial work across planning, execution, verification, and handoff, especially for multi-step tasks, phase-based delivery, or safe parallelization decisions. Choose between a quick path and a phase path, then route to specialized skills instead of replacing them. This skill should not imply delegation by default; use it to decide the workflow first, and keep work local unless a narrower skill later proves parallelism is safe.
---

# Project Orchestration

## Overview

Use this skill as a thin top-level workflow selector for substantial work. It decides whether to stay lightweight or become phase-based, how to structure parallel waves safely, what verification depth is needed, and what handoff state must be preserved.

## Core Rule

Route to specialized skills instead of replacing them with one generic process.

Use this skill to decide:

- whether the task should use a quick path or a phase path
- whether parallel execution is safe
- what verification layers are required
- whether a handoff or resume record is needed

## Routing Heuristics

Use this skill when the first problem is "what workflow should this task follow?"

- If the user mainly needs a concise implementation plan and the execution shape is already obvious, use `writing-plans`.
- If the task is clearly a migration or compatibility-sensitive multi-phase refactor, use `large-refactor`.
- If the task may or may not need phases, waves, or handoff and you need to choose the path first, use this skill.

## Operating Modes

Choose exactly one mode before doing substantive work.

### Quick Task

Use the quick path when all are true:

- the task is narrow or low risk
- the change does not require staged rollout
- there is no meaningful dependency graph to manage
- focused verification is enough
- the likely issue is a localized validation-harness or setup mismatch rather than a multi-module product change

Quick path:

1. Restate the goal and likely files or areas.
2. Execute directly with the relevant specialized skill if needed.
3. Run focused verification.
4. Persist durable context only if the task revealed something worth keeping.

### Phase Task

Use the phase path when one or more are true:

- the work spans multiple modules or systems
- ordering constraints matter
- safe parallelization depends on dependency analysis
- the work may continue across multiple sessions
- a migration, milestone plan, or staged rollout is safer than a single pass

Phase path:

1. List the non-negotiable requirements.
2. Map the brownfield surface area.
3. Plan phases and dependency waves.
4. Execute by phase.
5. Verify in layers.
6. Leave a handoff if the work is not truly done.

## Non-Negotiable Requirements

Before planning, list the requirements that must not silently disappear.

Include when relevant:

- user-visible behavior that must be preserved
- compatibility or migration constraints
- explicit user requests that are easy to weaken during planning
- verification or rollout requirements

Do not let the plan quietly narrow scope just because a smaller change is easier to implement.

## Brownfield Mapping

For existing repositories, map the real execution path before planning large work.
When symbol-aware tooling is available for the active repository, anchor this map in Serena-first navigation instead of broad file reads.

Capture only the minimum useful map:

- entrypoints
- owning modules
- registration or dependency wiring
- shared contracts or schemas
- verification entrypoints such as tests, builds, or smoke checks
- known risk zones

If a domain-specific mapping skill exists, use it instead of writing a generic map from scratch.

## Wave Planning

For phase tasks, split execution into waves based on dependency order.

Wave rules:

- tasks in the same wave must be independently executable
- each task must have explicit file or module ownership
- do not parallelize tasks that write the same file or unstable shared interface
- keep critical-path tasks local when the next step depends on them immediately
- use sidecar parallel work for exploration, isolated implementation, or independent verification

Prefer vertical slices over horizontal layers when assigning work.

## Verification Layers

Choose verification depth that matches the task.

- implementation verification: build, lint, typecheck, targeted tests
- behavior verification: the changed workflow, endpoint, page, or contract behaves as intended
- delivery verification: the full user requirement is covered, not just the easiest subset

Do not stop at "tests passed" when the task also requires behavior or rollout validation.

## Handoff And Resume

If the task is likely to continue later, leave a compact handoff.

Capture:

- current phase and wave
- what is done
- what remains
- blockers or risks
- the exact next recommended step

Store this in the narrowest correct place using the persistence workflow rather than inventing a new documentation system for every task.

## Skill Routing

Use this skill to choose and combine other skills deliberately.

- Use `writing-plans` for a concise implementation plan.
- Use `large-refactor` for multi-phase migrations or compatibility-sensitive changes.
- Use `parallel-execution` when multiple roles, subagents, or parallel waves may be useful.
- Use the platform-specific delegation capability after the parallelization decision when a concrete subagent prompt, read/write boundary, or independent verifier pass is needed.
- Use `serena-workflow` by default when Serena project activation, memory, or symbol-first brownfield mapping should anchor the task.
- Use `csharp-symbolic-workflow` for .NET and C# brownfield tracing, DI wiring, and cross-project impact analysis.
- Use `database-workflow` for database schema lookup, data inspection, SQL performance analysis, and explicit PostgreSQL or SQL Server writes through the local wrappers.
- Use `document-workflow` for PDF, Word, Excel, PowerPoint, CSV/TSV, Markdown conversion, or file deliverables where format fidelity matters.
- Use `security-review` when security is the primary objective or the touched code handles credentials, auth, PII, payments, uploads, webhooks, shell execution, or untrusted input.
- Use `dependency-upgrade` for package, framework, SDK, lockfile, peer dependency, and major-version migration work.
- Use `release-workflow` for changelogs, release notes, version bumps, tags, GitHub releases, or package publishing checks.
- Use `mcp-builder` when building or changing Model Context Protocol servers, clients, tools, resources, prompts, or transports.
- Use `systematic-debugging` for unclear failures.
- Use `test-driven-development` when tests are a practical driver of the change.
- Use `code-review` for final risk review.
- Use `agents-self-evolution` for durable context and resume notes.

Do not invoke every related skill by reflex. Route only to the ones that materially reduce error for the current task.

## Output Expectations

For quick tasks, produce:

- the chosen path
- the intended execution area
- the focused verification

For phase tasks, produce:

- the chosen path
- the non-negotiable requirements
- the brownfield map summary
- the phase and wave breakdown
- the verification layers
- the handoff shape if the task may continue later
