# Migration Patterns

Choose the smallest pattern that preserves safety.

## 1. Wrapper Or Adapter

Use when the new implementation can satisfy the old interface for a while.

- Keep old callers untouched initially
- Route them through a temporary compatibility layer
- Migrate callers incrementally

## 2. New Path Beside Old Path

Use when the new shape is too different to hide behind one interface.

- Introduce parallel code paths
- Move one caller group at a time
- Cut over only when the old path has no supported consumers

## 3. Dual Read Or Dual Write

Use when storage or message formats are changing.

- Prefer short-lived dual behavior
- Add observability to compare old and new outputs
- Remove dual behavior as soon as confidence is established

## 4. Capability Flag Or Switch

Use when rollout risk is significant.

- Gate the new path with a clear switch
- Define who can enable it and how to revert it
- Avoid leaving permanent dormant code after migration

## Selection Heuristics

- Use adapters for interface changes with stable semantics
- Use parallel paths for major semantic differences
- Use dual behavior only for data or integration migrations
- Use flags when operational rollback matters more than code simplicity
