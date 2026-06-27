---
name: code-optimization
description: Use when the user asks to optimize, improve, clean up, or refactor code and the main need is to choose the right optimization axis, constrain the scope, preserve behavior, and produce a measurable or explainable improvement without accidental rewrite drift.
---

# Code Optimization

Use this skill when the user wants "better" code but has not fully specified what kind of better matters most.

The goal is to turn vague optimization requests into disciplined improvement work instead of broad rewrites.

If the optimization axis is already clearly `maintainability` and the work is mainly about reuse, cohesion, abstraction boundaries, or file health, you may go directly to `code-maintainability` instead of loading this skill first. Use this skill as the entry point when the optimization axis is unclear, mixed, or likely to broaden during the task.

## Default Contract

Before editing, establish these points:

1. **Optimization axis**
   - `maintainability`
   - `architecture`
   - `performance`
   - `reliability`
   - `developer-experience`
2. **Behavior boundary**
   - what must stay externally the same
   - what may change if the user explicitly asked for it
3. **Scope boundary**
   - the owning file, module, or workflow
   - what is out of scope for this pass
4. **Evidence plan**
   - what proof will show the optimization helped
   - what verification will catch accidental regressions

If the optimization axis materially changes the plan and is still ambiguous, clarify first. Otherwise, state the assumed axis briefly and continue.

## Axis Guide

### Maintainability

Use when the main problem is duplication, file bloat, unclear helpers, awkward call sites, or hard-to-change code.

- Pair with `code-maintainability`.
- If ownership is muddy or wrappers are shallow, add `architecture-deepening`.
- Explain what duplication, caller knowledge, or cohesion problem was reduced.

### Architecture

Use when the main problem is wrong ownership, repeated orchestration, leaking invariants, or too many thin layers.

- Start with an owner-and-seam check.
- Pair with `architecture-deepening`.
- Use `large-refactor` if the cleanup needs phased rollout or compatibility preservation.
- Explain which owner changed and what complexity is now hidden behind it.

### Performance

Use when the main problem is latency, throughput, memory, query cost, bundle size, rendering, or unnecessary work.

- Gather bottleneck evidence before changing code when practical.
- Pair with the relevant domain skill and use `performance` or `core-web-vitals` when the task is web-focused.
- Prefer targeted fixes over speculative rewrites.
- Report before-and-after evidence when available, or state why measurement was impractical.

### Reliability

Use when the main problem is flaky behavior, weak validation, error handling gaps, race conditions, or regression-prone branching.

- Pair with `systematic-debugging` if the root cause is not already clear.
- Strengthen tests, checks, or invariants close to the risk.
- Explain what failure mode was prevented or made more observable.

### Developer-Experience

Use when the main problem is repeated setup, noisy test scaffolding, awkward tooling, poor readability, or slow local iteration.

- Improve the narrowest workflow that is repeatedly wasting effort.
- Prefer helpers, fixtures, scripts, or documentation that remove recurring friction without hiding important behavior.
- Explain which repeated task became easier or safer.

## Execution Rules

- Preserve external behavior unless the user explicitly asked for a behavior change.
- Prefer the smallest high-leverage change over a broad rewrite.
- Start with one primary optimization axis. Add `code-maintainability`, `architecture-deepening`, or other paired skills only when the chosen axis or emerging risk clearly requires them.
- Do not mix several optimization axes silently; if the work broadens, state the additional axis.
- Do not refactor only for style if there is no clear risk, cost, or repeated pain being reduced.
- Add focused verification before broad cleanup so the optimization remains behavior-safe.

## Questions To Answer Before Finishing

- What optimization axis did I use?
- What concrete problem did I reduce?
- What stayed behaviorally the same?
- What evidence supports the improvement?
- What larger cleanup did I intentionally leave out of scope?

## Output Expectations

When this skill is active, the result should usually state:

- the chosen optimization axis
- the scope boundary
- the concrete improvement made
- the verification or evidence gathered
- any intentionally deferred follow-up work
