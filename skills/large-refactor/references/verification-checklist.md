# Verification Checklist

Use this before declaring a refactor phase or the overall migration complete.

## Per Phase

- The stated invariants still hold
- The focused tests for the changed surface pass
- A realistic end-to-end path was exercised if behavior crosses module boundaries
- Observability or logging added for the migration is reviewed and either kept intentionally or removed
- Rollback is still possible if more phases remain

## Final Completion

- All supported callers use the new path
- Temporary adapters, flags, aliases, or dual behavior are removed or explicitly retained for a reason
- Old tests that validated deprecated behavior are updated or removed
- Documentation, examples, and interfaces reflect the final architecture
- No hidden dependency on the old path remains
