---
name: parallel-execution
description: Use only when multiple roles, subagents, or parallel workstreams are genuinely under consideration and you need to decide whether parallelization is actually safe. This skill should act as a brake as much as an enabler. Split work into dependency-safe waves only when ownership is explicit, the critical path stays local, and coordination cost will not outweigh the gain. Prefer serial execution when in doubt.
---

# Parallel Execution

## Overview

Use this skill to decide whether work should be parallelized at all, then split it into safe waves with clear ownership. Favor throughput only when it does not increase merge risk, coordination cost, or confusion on the critical path.

## Decision Rule

Parallelize only when it materially improves time or quality.

Parallel work is a good fit when all or most are true:

- tasks are independent or can be separated into clean dependency waves
- ownership boundaries are clear
- the results do not block the immediate next local step
- the write sets do not overlap
- verification can run independently

Stay serial when one or more are true:

- multiple tasks would write the same file or unstable interface
- the next step depends immediately on the result
- the task is short enough that coordination would dominate
- the interface is still changing
- the work is mostly exploration with heavy shared context

## Roles

Use roles as execution boundaries, not as theater.

- main agent: owns the critical path, integration, and final judgment
- explorer: answers a narrow read-only question about the codebase
- worker: owns a bounded implementation slice with an explicit write boundary
- verifier: runs independent checks or focused review without re-implementing the change

Do not invent extra roles unless they change execution behavior in a concrete way.

## Wave Planning

Plan work in waves.

- Wave 1 contains dependency-independent tasks that can run in parallel.
- Wave 2 contains tasks that depend on Wave 1 outputs.
- Continue only as far as useful; do not create ceremonial waves.

For each wave, define:

- purpose
- owner or role
- files or modules owned
- expected output
- blocking dependencies
- verification

## Ownership Rules

Each parallel task must have explicit ownership.

- assign by vertical slice when possible
- name the modules or files a worker owns
- tell workers not to revert or overwrite unrelated edits
- keep shared interfaces stable before parallelizing downstream edits

Prefer this:

- Worker A owns one API slice and its tests
- Worker B owns a separate UI slice

Avoid this:

- Worker A changes all DTOs while Worker B changes all handlers that depend on the same DTOs

## Critical Path Rule

Do not delegate the immediate blocking task just because parallelism is available.

First decide what the main agent should do locally right now. Then delegate only sidecar work that can progress independently.

Good sidecar work:

- mapping references in a separate module
- implementing a disjoint file set
- running independent verification

Bad sidecar work:

- the one fix needed before any other step makes sense

## Anti-Patterns

Avoid:

- duplicating the same investigation across multiple agents
- splitting by technical layer when dependencies cross layers tightly
- parallelizing before the target architecture or interface is stable
- using extra agents for small tasks that could be finished faster locally
- asking multiple agents to edit the same file set

## Handoff And Integration

When a parallel wave finishes:

- review returned changes quickly
- integrate or refine before starting dependent work
- record any ownership, interface, or merge assumptions that matter for later waves

If the task pauses mid-wave, leave a short handoff with the active wave, owned areas, completed subtasks, and next integration step.

## Codex Subagents

Use `codex-subagent` after this skill when a wave should be delegated through `codex exec`.

This skill owns the decision about whether parallel work is safe. `codex-subagent` owns the mechanics of the delegation prompt, model choice, read/write boundary, and returned evidence integration.

## Output Expectations

When using this skill, produce:

- whether the task should stay serial or become parallel
- the reason for that decision
- the wave breakdown when parallel work is chosen
- ownership boundaries for each parallel task
- the integration and verification plan
