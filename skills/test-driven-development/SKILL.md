---
name: test-driven-development
description: Use when implementing a feature, bug fix, or behavior change where tests are practical and valuable. Write or update a focused failing test first, make it pass with minimal code, and verify the relevant test scope stays green.
---

# Test First

Use this skill when test-first development is the right tool for the task. Prefer it for behavior changes, bug fixes, and non-trivial features with an existing test harness.

## Core Rule

Work in vertical slices, not horizontal batches.

Do not write a pile of tests first and then a pile of implementation. Write one behavior test, make it pass with the smallest useful change, then decide the next slice.

## Default Loop

1. Write or update the smallest test that demonstrates the desired behavior.
2. Run it and confirm it fails for the expected reason.
3. Implement the minimal production change.
4. Re-run the focused test.
5. Run any nearby tests needed to catch regressions.
6. Refactor only while green.

## Planning Before The First Test

Before writing code, quickly align on:

- the public interface or externally visible behavior being changed
- the highest-value behaviors to protect
- the best existing fixtures, helpers, builders, auth setup, or test seams to reuse

If the task is large or ambiguous, use `clarify-with-repo-context` or `writing-plans` first instead of guessing the first test.

## Good Use Cases

- Fixing a reproducible bug
- Adding behavior to a tested module
- Refactoring code whose behavior must stay stable

## Skip Or Soften It When

- The task is a one-off script, config tweak, or prototype
- There is no realistic test harness and adding one would dominate the task
- The user explicitly prefers a different workflow

If you skip test-first work, say why and use the next best verification method.

## Test Guidance

- Prefer one focused test over a large matrix.
- Test observable behavior, not private implementation details.
- Use real code paths when feasible; mock only true boundaries.
- Name the test after the behavior being protected.
- Reuse existing builders, fixtures, fake servers, auth helpers, database setup, and assertion helpers before creating new test infrastructure.
- Extract repeated test setup only when it represents the same scenario or domain concept; keep one-off setup local to the test.
- Avoid tests that mainly lock down data shape, internal call order, or helper boundaries unless that behavior is the public contract.
- If a refactor that preserves behavior would break the test, the test is probably too coupled to implementation.

## Slice Discipline

Avoid these failure modes:

- writing several tests before running any of them
- implementing speculative future behavior not required by the current failing test
- treating signatures, DTO shape, or internal helpers as the main thing under test

Preferred cadence:

1. one failing test
2. one minimal production change
3. one passing test
4. optional cleanup while still green

## Verification Checklist

- The new or updated test failed before the implementation, when practical.
- The focused test passes after the change.
- Related tests or checks were run if the blast radius is larger than one unit.
- Behavior-level verification was considered when a passing test alone is not enough to prove the user-facing result.
- Test code remains maintainable: setup is not duplicated across new tests, helpers are not over-generic, and assertions describe behavior rather than private implementation shape.
- Any missing coverage or skipped verification is called out explicitly.
- Refactoring, if any, happened only after the relevant tests were green.

## Layered Verification

Use tests as the primary implementation proof, but do not confuse them with full task acceptance.

- implementation verification: focused test and nearby regression checks
- behavior verification: endpoint, UI flow, contract, or externally visible behavior when applicable
- delivery verification: confirm the implemented behavior still matches the user's requested outcome

If tests are impractical, replace them with the next best concrete verification and say what confidence remains missing.
