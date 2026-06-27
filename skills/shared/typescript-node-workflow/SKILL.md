---
name: typescript-node-workflow
description: Use when working in TypeScript or Node.js backends, CLIs, scripts, APIs, workers, or services where repo conventions, runtime wiring, package scripts, test harnesses, or framework patterns matter. Prefer this for Express, Fastify, NestJS, serverless functions, Node CLIs, and brownfield TypeScript service repositories.
---

# TypeScript Node Workflow

Use this skill when TypeScript or Node.js is the main backend or service surface and the task needs repository-aware implementation guidance.

The goal is to keep Node and TypeScript work aligned with the repo's runtime, scripts, module system, testing setup, and framework conventions.

## When To Use

Use this skill when:

- editing TypeScript or JavaScript backend code, APIs, workers, CLIs, or scripts
- working in Express, Fastify, NestJS, serverless, queue workers, or Node service repos
- debugging build, runtime, import, ESM/CJS, script, or test-harness issues in Node projects
- adding or changing package scripts, tsconfig behavior, runtime wiring, or validation logic
- tracing how routes, handlers, clients, DTOs, and services connect in a TypeScript backend

Pair with:

- `serena-workflow` for symbol-aware brownfield tracing
- `systematic-debugging` when root cause is unknown
- `test-driven-development` for behavior-safe changes
- `code-maintainability` for non-trivial implementation work
- `dependency-upgrade` for package or runtime upgrades

## Default Flow

1. Confirm the repo's runtime and package-manager shape.
2. Reuse existing package scripts, tsconfig conventions, framework wiring, and test commands.
3. Keep changes in the narrowest owner: route, controller, service, command, worker, or shared contract.
4. Prefer focused verification before broad rebuilds.
5. Preserve the existing module system and build path unless the task explicitly changes it.

## Environment And Tooling

Prefer the repo's existing workflow first:

- `npm`, `pnpm`, `yarn`, or `bun` already used by the repo
- repo-owned package scripts such as `test`, `build`, `lint`, `typecheck`, `dev`, or targeted script variants
- the existing `tsconfig*.json`, framework CLI, and environment-loading pattern
- framework-native test harnesses already present in the repo

Do not silently switch package managers or module systems.
If the repo is ESM, do not patch around imports with CommonJS shortcuts.
If the repo is CommonJS, do not force an ESM migration as part of a local task.

## Coding Rules

- Reuse existing route, controller, service, schema, DTO, and client patterns before adding new layers.
- Keep transport concerns, validation, business logic, and persistence boundaries aligned with the existing architecture.
- Avoid adding broad helpers when an existing owner already expresses the concept.
- Respect existing error-handling, logging, and configuration patterns.
- Prefer repo-native validation libraries and request schemas instead of introducing a new validator for one endpoint.

## Framework Guidance

### Express / Fastify / NestJS / Serverless

- Follow the repo's existing registration and dependency wiring style.
- Keep request parsing, auth, validation, orchestration, and domain work in the same seams the repo already uses.
- Prefer framework-native test or bootstrap helpers already in the repo.

### CLI / Worker / Script Work

- Prefer existing command runners and package scripts.
- Keep long-running worker orchestration separate from one-off script behavior.
- Make destructive operations explicit and easy to verify.

## Verification

Prefer the smallest convincing check:

- targeted test file or test name
- focused `build` / `typecheck` / `lint` scope when available
- targeted route, handler, or CLI invocation
- broader package verification only when the blast radius requires it

If the repo already has Playwright or browser verification for the changed path, use the dedicated browser skill rather than inventing a separate harness.

## Output Expectations

When using this skill, state:

- the runtime and package-manager assumptions followed
- the main owners changed
- the focused verification run
- any ESM/CJS, build, or env uncertainty still remaining
