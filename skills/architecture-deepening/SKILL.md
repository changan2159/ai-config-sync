---
name: architecture-deepening
description: Use during brownfield feature work, refactors, and review to run a lightweight owner-and-seam check before coding, then deepen the analysis when file bloat, shallow wrappers, duplicated orchestration, or muddy ownership appear. Apply it broadly across non-trivial development in existing code, but keep the default pass light unless architectural entropy is the main risk.
---

# Architecture Deepening

Use this skill when the risk is not only correctness, but codebase entropy.

The goal is to stop agents from solving every task by adding more lines to the nearest file, introducing thin pass-through helpers, or spreading one concept across many shallow layers.

## Core Rule

Do not just move code around. Concentrate complexity into a better owner.

A good extraction reduces caller knowledge, reduces repeated orchestration, and makes future changes more local. A bad extraction creates one more file or helper that callers still need to mentally inline.

## Operating Modes

Use this skill in two modes.

### 1. Pre-Code Pass

Run this lightweight check before most non-trivial development in existing code:

1. Identify the concept being changed.
2. Identify the current owner.
3. Decide whether the owner should absorb the change, or whether a clearer domain-shaped seam is emerging.
4. Check whether callers are doing work that should move behind that seam.

This pass should be quick. It is not a request for a long architecture document.

### 2. Deepening Pass

Switch to the heavier lens when the change starts showing real entropy signals:

- file bloat
- shallow wrappers
- duplicated orchestration
- muddy ownership
- hard-to-trace behavior scattered across multiple thin files

In this mode, do the deeper analysis and restructuring work described below.

## Deterministic Assist

When you need a quick structural warning pass against a git worktree, run:

```bash
python3 /home/admin101/.codex/skills/architecture-deepening/scripts/architecture_guardrail.py <repo-path>
```

The script is heuristic and intentionally lightweight. It currently warns on:

- existing large files that keep growing in the diff
- changed or newly added files with generic names such as `helper`, `util`, `manager`, or `common`

Treat these warnings as prompts to re-run the owner/seam check, not as automatic proof that the change is wrong.

## When To Use

Use this skill when one or more are true:

- a non-trivial development task touches existing brownfield code and needs an owner/seam decision before edits begin
- a touched file is already large, mixed-purpose, or hard to scan
- the change adds another branch of logic to an already busy service, component, handler, or controller
- the same orchestration, mapping, validation, or permission logic is appearing in multiple places
- the agent is about to create a wrapper that mostly forwards arguments
- the task needs refactoring or review to keep future work from getting worse

Pair this with:

- `code-maintainability` for general reuse and file-boundary discipline
- `code-review` for final maintainability findings
- `large-refactor` when the cleanup must happen in phased rollout form

## Main Smells

Treat these as architectural friction, not cosmetic issues:

- long files accumulating unrelated responsibilities
- helpers that mostly rename or forward existing calls
- services that coordinate many unrelated workflows
- repeated caller-side branching that should live behind one seam
- DTO or config plumbing duplicated across many call sites
- new abstractions with vague names such as `helper`, `util`, `manager`, or `common`
- call flows where understanding one behavior requires hopping through many tiny files

## Deepening Heuristics

Prefer changes that increase leverage and locality.

- **Leverage**: callers get more useful behavior from a smaller interface.
- **Locality**: related change tends to stay in one place instead of scattering across callers.

Good deepening moves:

- extract a domain-named service, policy, mapper, validator, query object, or workflow helper that owns the full decision
- turn repeated orchestration into one operation with a clear contract
- move branching to the owner that already knows the invariants
- split one mixed-purpose file into a small number of cohesive owners

Weak moves:

- extracting a helper that still forces each caller to assemble half the inputs and decisions
- creating a pass-through wrapper just to shorten one line
- moving code to a new file without improving ownership or interface shape
- replacing duplication with a generic option bag that hides multiple behaviors

## The Deletion Test

Before introducing or keeping an abstraction, ask:

If I delete this module, does complexity reappear across multiple callers, or does nothing meaningful change?

- if complexity would reappear across callers, the module may be earning its keep
- if the module mostly disappears without cost, it is probably shallow

Use this test on new helpers, services, hooks, mappers, and utility files.

## File Growth Guardrails

Do not use line count alone as the trigger. Look for responsibility growth.

Pause and reconsider structure when a change would make a file:

- own UI or HTTP concerns plus domain logic plus mapping or validation
- gain another private-helper region that mirrors an existing workflow
- add one more case to a branching structure that is already hard to scan
- require scrolling through many unrelated concepts to understand one behavior

When that happens, prefer one of these:

- local private extraction if reuse is not real yet
- adjacent new owner with a domain name if a distinct concept is emerging
- caller cleanup plus one deeper seam if repeated orchestration is spreading

## Ownership Questions

Before writing the code, answer:

1. What is the real concept being added or changed?
2. Which existing file or module should naturally own that concept?
3. Are callers currently doing work that the owner should absorb?
4. If I add a new abstraction, what caller knowledge disappears?
5. If no caller knowledge disappears, why am I extracting it?

If you cannot answer these cleanly, do not rush into a new abstraction.

For ordinary feature work, answering these questions may be enough. Only escalate to deeper restructuring if the answers reveal a real ownership problem.

## Implementation Rules

- Prefer domain-shaped names over technical placeholders.
- Keep interfaces small but meaningful; small alone is not enough.
- Let the owner perform the full decision when practical, not just a fragment of it.
- Keep related invariants, branching, and mapping together when they change together.
- Avoid creating a shared abstraction before there is a real ownership story.
- Avoid mega-files and mega-functions, but also avoid atomizing behavior into many paper-thin files.

## Review Lens

When reviewing or self-reviewing a change, ask:

- Did this change deepen an existing owner or just append more code to it?
- Did any new helper remove real caller complexity?
- Is there still duplicated orchestration that should be pulled behind one seam?
- Did the change introduce a shallow abstraction or vague file name?
- Is the touched file more cohesive after the change, or only longer?

If the honest answer is "only longer", the architecture likely regressed.

## Finish Check

Before declaring a non-trivial coding task done, run a short deep-module check:

1. Name the concept that changed.
2. Identify its owner after the change.
3. State what complexity is now hidden behind that owner.
4. Identify any remaining shallow wrapper, repeated orchestration, or bloated file that the change left behind.
5. Fix the local issue if it is small; otherwise call out the residual architectural debt explicitly.

## Output Expectations

When this skill is active, the work should usually produce one or more of:

- a more cohesive owner for the changed behavior
- fewer caller responsibilities
- fewer shallow wrappers
- a clearer split between orchestration and implementation
- an explicit note when the current task should not absorb a broader cleanup

## Avoid

- architecture astronautics
- generic utility dumping grounds
- extracting names without extracting responsibility
- splitting files so aggressively that the behavior becomes harder to trace
- broad cleanup unrelated to the requested change
