---
name: pi-autonomy-orchestrator
description: Use Pi-native goal, prune, fallback, and delegation surfaces automatically during substantial Pi development work.
---

# Pi Autonomy Orchestrator

Use this skill only in Pi sessions.

The purpose is to make Pi use its installed native capability surfaces automatically during real development work, instead of waiting for the user to invoke commands manually.

## When To Use

Use this skill when one or more are true:

- the task is a non-trivial coding task in Pi
- the work is expected to run for many turns
- the work spans files or modules
- the session is likely to accumulate significant tool output
- the task benefits from delegation or a planning gate

Do not use it for tiny one-shot answers or trivial edits.

## Core Rule

Prefer Pi-native runtime surfaces when they materially improve execution:

- `pi-goal` for persistent long-running objectives
- `pi-plan-mode` for planning gates on large work
- `pi-subagents` for bounded sidecar delegation
- `pi-context-prune` for automatic context compaction
- `pi-context-usage` and `pi-cache-graph` for observability when context pressure or cache behavior matters
- `pi-fallback-provider` for model failover resilience

These are complements to shared skills, not replacements for them.

## Automatic Usage Policy

### Goals

When the user asks Pi to carry a substantial implementation from start to finish, prefer setting or continuing a Pi-native goal instead of relying only on conversational intent.

Use `pi-goal` when:

- the objective is expected to take many turns
- success criteria can be stated concretely
- the session should continue working until done

Good examples:

- build a new subsystem
- finish a migration
- implement and verify a feature end-to-end
- clean up a large bug cluster with tests

Do not force `pi-goal` for quick exploratory turns.

### Planning Gate

Use `pi-plan-mode` before implementation when:

- the task crosses modules
- sequencing matters
- the work needs a phase boundary
- a wrong first edit would be expensive

If the task is obviously small and local, skip the planning gate.

### Delegation

Use `pi-subagents` only for bounded, non-overlapping sidecar work:

- independent verification
- targeted file discovery
- read-only review
- isolated implementation in a separate module when ownership is clear

Keep the critical path local.

### Context Management

Assume `pi-context-prune` is installed and configured.

For long-running tasks:

- rely on automatic pruning first
- use `pi-context-usage` or `pi-cache-graph` when you need to understand context growth or cache behavior
- do not manually summarize away important context prematurely if the extension can preserve and compact it safely
- when Serena has surfaced important code structure, symbol ownership, or call-chain findings, write them to Serena project memory explicitly before context grows long; pi-context-prune compresses in-session window content and does not preserve Serena tool results with full precision after compaction — Serena file memory is the durable layer, in-context results are not

### Fallback

Assume `pi-fallback-provider` is installed.

Do not ask the user to switch models manually for transient provider failures unless there is evidence the configured fallback chain itself is broken.

## Pairing With Shared Skills

This skill should commonly route into shared skills:

- `project-orchestration`
- `writing-plans`
- `code-maintainability`
- `architecture-deepening`
- `code-review`
- `agents-self-evolution`

Pi-native surfaces handle runtime behavior.
Shared skills handle reasoning quality and repository workflow.

## Output Expectations

When this skill is active in Pi:

- substantial tasks should naturally use Pi-native planning, goal persistence, or delegation when appropriate
- long tasks should avoid context collapse by relying on pruning instead of manual cleanup
- transient model outages should not require manual switching when the fallback chain is healthy
