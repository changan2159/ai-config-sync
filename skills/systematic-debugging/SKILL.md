---
name: systematic-debugging
description: Use when a bug, test failure, build failure, validation failure, or unexpected behavior is not immediately obvious. Reproduce the issue, gather evidence, identify the root cause, and only then implement and verify a focused fix. Include test-harness or setup drift as an early hypothesis when the failure may come from outdated assumptions rather than product logic, and treat EF Core schema drift as a first-class hypothesis when database objects are missing.
---

# Systematic Debugging

Use this skill for non-obvious failures. The goal is to stop guess-and-check and get to a defensible root cause quickly.

## Core Rule

Build a feedback loop before you theorize.

If you can produce a fast, repeatable pass/fail signal for the bug, you can debug it. If you cannot, do not pretend the investigation is rigorous yet.

## Default Flow

1. Build the narrowest useful feedback loop.
2. Reproduce the issue consistently if possible.
3. Read the exact error, logs, or failing output.
4. Compare the broken path with a working path or recent change.
5. Rank 3-5 concrete hypotheses when the cause is not obvious.
6. Test the best hypothesis with the smallest useful probe.
7. Fix the root cause.
8. Verify the original failure is resolved and adjacent behavior still works.

If the failure crosses multiple modules, environments, or ownership boundaries, use `project-orchestration` to structure the work and `parallel-execution` only for sidecar investigation that does not block the next debugging step.

## Feedback Loop First

Prefer these repro harnesses in roughly this order:

1. a focused failing test
2. a minimal CLI or script invocation
3. a reproducible HTTP request against a local server
4. a browser automation flow when the failure is UI-driven
5. a throwaway harness that exercises the failing code path directly

Improve the loop if needed:

- make it faster by cutting unrelated setup
- make it sharper by asserting on the exact symptom
- make it more deterministic by pinning time, data, and environment

Do not move into hypothesis testing until you trust the loop.

## Evidence First

- Quote the actual error or symptom precisely.
- If multiple components are involved, inspect the boundaries between them.
- Add temporary logging or instrumentation when the break point is unclear.
- Avoid stacking multiple speculative fixes.
- Schema failure checklist:
  - For `relation does not exist`, missing column, missing constraint, or similar database object errors, verify migration history and schema drift before assuming the query code is wrong.
  - If the project uses EF Core, compare the current model against the latest migration snapshot early in the investigation.
  - Confirm whether the target database actually applied the migration that introduced the schema change.
  - If confirming the live PostgreSQL or SQL Server schema/data is necessary, use `database-workflow` and the local database wrappers instead of raw database CLI output.
  - Only after schema drift is ruled out should you spend time on the query, mapping, or include chain.

## Harness Drift Check

When the failure comes from tests, smoke suites, CI, or local validation scripts, first distinguish harness drift from product regression.

- Check repository root assumptions, solution names, fixture bootstrap paths, environment variables, default credentials, and seed-data expectations.
- If the application builds or a narrower verification step passes but a broader suite fails before exercising the target behavior, suspect test or validation infrastructure first.
- Fix harness drift with the smallest possible change before debugging business logic.
- After repairing the harness, rerun the narrowest failing test to reveal any remaining real regression.

## Hypothesis Discipline

When several causes are plausible, avoid single-path anchoring.

- Write down 3-5 ranked hypotheses.
- Make each one falsifiable: "If X is the cause, changing Y should produce Z."
- Test one variable at a time.
- Prefer a debugger or narrow probe over broad logging.

If the problem is non-deterministic, focus first on raising the reproduction rate. A flaky bug with a 50 percent hit rate is debuggable. A 1 percent vibe is not.

## Debugging Boundaries

For broad failures, map the failing path before changing code:

- entrypoint or trigger
- failing component boundary
- recent change or divergence point
- minimal reproduction or failing command
- likely owners or modules involved

Keep the first debugging wave read-heavy. Do not parallelize speculative fixes.

## Instrumentation Rules

- Tag temporary debug logs with a unique marker so they can be removed cleanly.
- Do not leave throwaway harnesses or probes undocumented if they remain in the tree.
- For performance regressions, measure first. Prefer timings, profilers, query plans, or comparable baselines over generic logs.

## Good Triggers

- A test is failing and the reason is not obvious.
- A runtime bug has multiple plausible causes.
- A build or CI failure may come from config, environment, or code.
- Two or more attempted fixes have already failed.

## Red Flags

- "This is probably X, let me just change it."
- Bundling several unrelated fixes into one attempt.
- Declaring success without reproducing the original issue.

## Verification Checklist

- A credible feedback loop existed before the main fix.
- The root cause is stated explicitly.
- The fix maps to that cause, not just the surface symptom.
- The original reproduction, test, or failing command now passes.
- Temporary diagnostics are cleaned up or intentionally kept.
- For schema-related fixes, confirm the migration exists, was applied to the target database, and corresponds to the model change that introduced the failure.

If the investigation pauses before resolution, leave a short handoff with the latest evidence, rejected hypotheses, current best hypothesis, and the next probe to run.
