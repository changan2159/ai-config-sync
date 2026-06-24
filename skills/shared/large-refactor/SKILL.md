---
name: large-refactor
description: Use when it is already clear that the task is a large refactor, migration, or architectural change spanning multiple modules, requiring phased rollout, or preserving compatibility while changing internals. Plan the stages, define invariants, isolate write boundaries, and verify each phase before broad cleanup. For initial workflow selection when that is not yet clear, use `project-orchestration` first.
---

# Large Refactor

Use this skill for changes that are too large to treat as a normal feature edit. The goal is to keep momentum without losing control of compatibility, scope, or verification.

## When To Use

Use this skill when one or more of these are true:

- The change spans multiple modules, packages, or services.
- You need to migrate callers from an old API or data shape to a new one.
- The safest path is a staged rollout rather than a single cutover.
- Temporary adapters, shims, or dual-write behavior may be needed.
- A simple implementation plan is not enough because sequencing and invariants matter.

Do not use this skill for ordinary single-module cleanup. Use `writing-plans` for smaller multi-step work.

If the main task is a package, framework, SDK, lockfile, or major dependency migration, use `dependency-upgrade` first. Combine with this skill only when the upgrade becomes a broad architectural migration with staged compatibility work.

## Core Rules

1. Define what must not break before changing structure.
2. Prefer staged migration over big-bang rewrites.
3. Keep old and new paths clearly separated while both exist.
4. Remove temporary compatibility code only after consumers have moved.
5. Verify each phase independently before starting the next one.

## Workflow

### 1. Frame The Refactor

- State the target architecture or end state in one short paragraph.
- List the current constraints: compatibility requirements, deadlines, data safety, rollout limits, or team constraints.
- Read [references/invariants.md](references/invariants.md) and write down the invariants that must hold through every phase.

### 2. Map The Surface Area

- Identify the modules, files, entry points, data contracts, and tests touched by the change.
- Mark which parts are producers, consumers, adapters, and shared types.
- Produce a compact brownfield map before locking the phase plan.
- Read [references/migration-patterns.md](references/migration-patterns.md) and choose the smallest migration pattern that fits.

Brownfield map minimum:

- entrypoints and their owning modules
- registration or dependency wiring that makes the path live
- shared contracts and compatibility boundaries
- test or verification entrypoints
- the highest-risk zones for rollback or regression

### 3. Split Into Phases

- Break the work into phases that can each be verified.
- Each phase should have a clear entry condition, completion condition, and rollback story.
- Prefer phases like: prepare, introduce new path, migrate consumers, switch default, remove old path.
- For each phase, decide whether execution should be serial or split into dependency-safe waves.
- Read [references/phase-template.md](references/phase-template.md) and use that shape when writing the plan.

### 4. Choose Compatibility Strategy

- Decide whether to use adapters, feature flags, dual-read, dual-write, aliasing, or temporary wrappers.
- Keep temporary compatibility code narrow and easy to delete.
- Name temporary paths clearly so they do not become permanent by accident.

### 5. Execute Safely

- Work phase by phase, not by file category.
- Keep write boundaries explicit. If parallel work is safe, split by phase or module ownership.
- Treat each parallel batch as a wave with explicit dependencies and ownership.
- Prefer vertical feature slices over horizontal layer splits when both UI/API and internals change together.
- Avoid bundling opportunistic cleanup with migration work.

### 6. Verify And Clean Up

- Run the phase-specific checks before moving on.
- Verify each phase at three levels when relevant: implementation, behavior, and delivery completeness.
- After the final cutover, remove temporary code, dead callers, and old tests that no longer reflect supported behavior.
- Read [references/verification-checklist.md](references/verification-checklist.md) before declaring the refactor complete.

### 7. Leave A Handoff If The Work Spans Sessions

- Record the current phase and wave.
- Record what is complete, what is incomplete, and what is blocked.
- Record the next recommended action and any rollback-sensitive notes.
- Persist the handoff through the project context workflow instead of inventing a new ad hoc summary file unless the repo already uses one.

## Output Expectations

When using this skill, produce:

- A short statement of the target state
- A phased plan with verification for each phase
- Wave breakdown where parallel execution is safe
- The compatibility strategy
- The main invariants and risks
- The cleanup criteria for removing temporary code
- The handoff shape if the refactor is expected to continue later

## Avoid

- Big-bang rewrites unless the user explicitly wants that tradeoff
- Combining migration, redesign, and unrelated cleanup in one pass
- Removing old paths before all consumers have moved
- Vague phase names without checks or exit criteria
