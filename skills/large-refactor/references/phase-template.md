# Phase Template

Use a short, repeatable structure for each refactor phase.

## Suggested Format

### Phase <N>: <Name>

- Goal: what changes in this phase
- Scope: modules, callers, or data touched
- Entry condition: what must already be true
- Changes: the concrete implementation work
- Verify: the checks or tests that prove this phase is safe
- Exit condition: what allows the next phase to start
- Rollback: how to back out if verification fails

## Good Phase Names

- Prepare shared types
- Introduce compatibility adapter
- Migrate first consumer group
- Switch default path
- Remove deprecated implementation

## Bad Phase Names

- Refactor backend
- Cleanup stuff
- Final fixes
