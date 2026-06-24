# Invariants

Write these down before changing code. They are the guardrails that stay true across all phases.

## Typical Invariants

- Public API behavior that existing callers depend on
- Data format or persistence guarantees
- Error semantics that upstream systems expect
- Ordering, idempotency, or transactional guarantees
- Performance or latency constraints that cannot regress materially
- Deployment constraints such as backward-compatible rollouts

## Questions To Answer

- What behavior must remain stable while internals change?
- Which callers or systems cannot migrate immediately?
- What data cannot be rewritten or lost?
- What failures would be expensive to detect late?

## Usage

Turn the answers into a short list. Revisit the list at the start of every phase.
