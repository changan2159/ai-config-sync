---
name: code-review
description: Use when reviewing code changes for bugs, regressions, missing tests, maintainability risks, security concerns, duplicate logic, poor reuse, oversized files, or weak abstraction boundaries. Prioritize concrete findings with file and line references over generic style commentary or scoring. Pair with code-maintainability for non-trivial implementation quality review.
---

# Code Review

Review code like an engineer deciding whether the change is safe to merge.

## Review Order

1. Understand the intended behavior and scope of the change.
2. Look for correctness issues, regressions, and edge cases.
3. Check test coverage and whether the change is adequately verified.
4. Consider maintainability, performance, and security where relevant.
5. Mention style issues only if they affect clarity or create risk.

If the user asks primarily for a security audit, vulnerability review, secrets check, OWASP review, or auth/input-handling security pass, use `security-review` instead of treating security as a secondary code-review lens.

## Maintainability Lens

- Treat duplicated business logic, duplicated UI components, repeated method call patterns, parallel helper stacks, oversized mixed-purpose files, and avoidable new abstractions as review findings when they create drift or future change risk.
- Check whether the change missed an existing service, method, hook, DTO, serializer, component, query helper, validator, test fixture, framework feature, dependency, or project convention that should have been reused, extended, or composed.
- Check whether new abstractions are named after real domain concepts, live at the narrowest useful scope, and make call sites clearer rather than hiding multiple behaviors behind flags or generic option bags.
- Do not demand refactors unrelated to the reviewed change; only flag reuse, extraction, file-boundary, and abstraction issues that affect the safety, consistency, or maintainability of this change.

## Verification Lens

Treat verification as layered, not binary.

- implementation verification: build, tests, lint, typecheck, static checks
- behavior verification: the changed workflow or contract actually does what the user expects
- delivery verification: the change covers the full requested scope and does not silently omit requirements

When reviewing, call out which layer is missing if the change is under-verified.

## Output Expectations

- Lead with findings, highest severity first.
- Make each finding concrete: what is wrong, why it matters, and where it is.
- Include file and line references when available.
- Keep summaries brief and secondary.
- If there are no findings, say so explicitly and mention any residual risk or missing verification.

## Avoid

- Numeric scores
- Generic praise
- Listing minor nits before real risks
- Recommending refactors unrelated to the reviewed change
