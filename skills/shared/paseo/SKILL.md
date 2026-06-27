---
name: paseo
description: Use when an agent needs the Paseo CLI surface for spawning, listing, messaging, waiting on, and managing other agents or worktrees. This is the shared reference skill behind the repo-managed Paseo orchestration set and should be loaded before using `paseo-handoff`, `paseo-advisor`, `paseo-loop`, or `paseo-committee` when the current environment has `paseo` available.
---

# Paseo Reference

Use this skill as the shared reference for repo-managed Paseo orchestration. It teaches the current agent how to use the `paseo` CLI safely and predictably so delegation and review flows do not have to be reinvented ad hoc.

This skill is intentionally thin. It explains the command surface and the decision boundaries. Higher-level workflows live in:

- `paseo-handoff`
- `paseo-advisor`
- `paseo-loop`
- `paseo-committee`

## Purpose

Use Paseo when another coding agent should do bounded work on the same machine or on a paired remote daemon.

Paseo is a control plane. It does not replace the underlying provider CLI. It starts and manages provider-backed agents such as Claude Code, Codex, OpenCode, Copilot, or Pi.

## When To Use

Use this skill when:

- you need to create another agent for a bounded subtask
- you need to send follow-up instructions to an existing agent
- you need to wait for another agent before continuing
- you need logs, structured output, or worktree-backed execution
- another shared Paseo skill needs the CLI reference

Do not use it when:

- the task is simpler to finish locally
- the write boundary is unclear
- multiple agents would race on the same file or unstable interface
- the current issue is still basic exploration and delegation would add coordination overhead

## Core CLI Surface

The most important commands are:

```bash
paseo run "task"
paseo run --provider codex "task"
paseo run --detach --name api-review "task"
paseo run --worktree feature-x "task"
paseo send <id> "follow-up instruction"
paseo wait <id>
paseo logs <id> --tail 20
paseo attach <id>
paseo ls -a -g --json
```

Useful additions:

- `--provider <provider>` to pick the worker explicitly
- `--worktree <name>` when isolation matters
- `--detach` for background agents
- `--name <name>` when later coordination should use a stable name instead of an opaque ID
- `--output-schema <schema>` for structured verifier output
- `--host <target>` when operating a remote paired daemon instead of the local default

## Safe Usage Rules

Before launching another agent, decide:

1. what exact outcome it owns
2. what files or modules it may change
3. whether it is read-only, advisory, or allowed to edit
4. what verification signal determines success
5. whether the main thread can continue independently

Keep prompts self-contained. Include:

- task goal
- relevant files, modules, or commands
- constraints and forbidden scope
- expected output shape
- verification expectation

## Delegation Boundaries

Prefer these patterns:

- advisor: read-only second opinion
- handoff: bounded implementation or review slice
- loop: repeated worker/verifier cycle with explicit stop conditions
- committee: multi-agent analysis before implementation

Avoid these patterns:

- multiple workers editing the same file set
- asking an agent to “look around and do whatever seems best” without boundaries
- delegating the immediate critical-path task before the interface is stable
- using Paseo just to duplicate work already underway locally

## Review And Verification

When Paseo is used for verification or review:

- keep the verifying agent read-only when possible
- pass the smallest relevant diff or context
- prefer structured output for pass/fail style checks
- use `paseo wait` and `paseo logs` instead of guessing completion state

Example structured verifier:

```bash
paseo run --provider claude \
  --output-schema '{"type":"object","properties":{"criteria_met":{"type":"boolean"},"reason":{"type":"string"}},"required":["criteria_met"],"additionalProperties":false}' \
  "Review the current diff and decide whether the acceptance criteria are met."
```

## Interaction With Other Skills

Use this skill together with:

- `project-orchestration` when you first need to choose whether delegation is warranted
- `parallel-execution` when deciding whether multiple workers are actually safe
- `code-review` when the need is final risk review rather than orchestration mechanics
- `agents-self-evolution` when a verified Paseo workflow or command pattern should be persisted

## Output Expectations

When this skill is active, the agent should make explicit:

- whether Paseo is actually needed
- which provider or role is best for the subtask
- whether the launched agent is advisory, verifier-only, or allowed to edit
- how success will be observed
- when the main thread should wait versus continue
