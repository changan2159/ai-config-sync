# Shared Core Preferences

- Follow direct user instructions first, then repository-local instruction files and verified project docs, then this shared core.
- Prefer concise, client-friendly file references. Use absolute local paths when needed, and use client-native clickable link formats when supported.
- Prefer the simplest approach that solves the request. Match the existing codebase and workflow unless there is a concrete reason to diverge.
- Make the smallest coherent change that satisfies the request. Do not silently expand optimization, cleanup, or refactor tasks into broader rewrites.
- Default to UTF-8 for AI-maintained text, scripts, templates, and docs. In Python, pass `encoding="utf-8"` when reading or writing text.
- When adding dependencies, prefer pinned or exact versions over open ranges, and verify the package is maintained and not a typosquatting risk.
- Use `fetch` for version-sensitive external docs, changelogs, and API references instead of relying on memory.
- Use `node_repl` as a scratchpad for quick JavaScript validation when that is faster than creating temporary files.
- When a repo or host already provides managed runtime or workflow notes, follow those docs instead of improvising alternate repair paths.
- On this machine, use `/home/admin101/projects/2026/ai-config-sync/docs/shared/runtime/linux-serena-dotnet-host-notes.md` for Serena plus `.NET` host issues, and `/home/admin101/projects/2026/ai-config-sync/docs/shared/workflows/dotnet-workflow-defaults.md` for `.NET` and EF Core CLI defaults.

# Retrieval And Tool Choice

- For brownfield code retrieval, use indexed discovery first when available, symbol-aware confirmation second, and plain text search third for config keys, routes, JSON fields, SQL, logs, docs, and other string-driven behavior.
- Treat graph or index results as candidate discovery, not edit authority; confirm owners and edit targets with symbol-aware tools or direct reads before changing code.
- When querying an index or code graph, anchor with explicit symbol names, file stems, endpoint paths, or DTO names before broadening the query.
- Do not force symbol-aware tools for trivial localized edits, docs-only work, config-only work, build or test execution, or small styling tasks where setup costs more than it saves.
- Explore serially before parallelizing. Parallelize only after the owner, write boundary, and dependency order are clear.
- Prefer parallel work for information gathering, independent verification, and non-overlapping reads or edits after the write boundary is stable.
- Keep mainline implementation serial when tasks write the same file or module, depend on unstable interfaces, or directly determine each other's next step.

# Brownfield Change Discipline

- Treat a task as non-trivial when it crosses files, changes a public or shared interface, touches persistence, auth, billing, or state transitions, changes a user-visible workflow or contract, or requires adding or updating tests.
- Before non-trivial edits, run a lightweight owner-and-seam check: what concept is changing, which file or module owns it now, whether that owner should absorb the change or a clearer seam is emerging, and whether callers are doing work that should move behind that seam.
- Prefer reuse, extension, or composition before creating a new abstraction. Avoid vague helpers, pass-through wrappers, or generic `utils` modules when a domain owner already exists.
- If a file keeps growing without becoming more cohesive, caller-side orchestration repeats, or new helpers only rename and forward work, deepen ownership instead of adding one more layer.
- Escalate to `architecture-deepening` when file growth, shallow wrappers, repeated caller orchestration, or muddy ownership become the main structural risk.
- After non-trivial coding, debugging, review, or refactor work, do a brief end-of-task self-check for durable context worth preserving. Persist proven structure, business rules, verified commands, or repeated corrections in the narrowest correct place; keep weak inferences as open questions.
- Do not promote one-off troubleshooting notes, temporary workarounds, or unverified guesses into broad shared guidance; keep them in a narrower note or memory until they are proven durable.

# Optimization Requests

- When the user asks to optimize, improve, or refactor code, first classify the primary axis as `maintainability`, `architecture`, `performance`, `reliability`, or `developer-experience`.
- If the optimization axis would materially change the plan, clarify first. Otherwise, state the assumed axis briefly and continue.
- Preserve external behavior unless the user explicitly asks for behavior change.
- Prefer the smallest high-leverage change with clear benefit. Do not turn optimization into a broad stylistic rewrite.
- For maintainability or architecture optimization, explain what duplication, caller knowledge, ownership confusion, or file bloat was reduced.
- For performance optimization, gather before-and-after evidence when practical; if measurement is impractical, explain the bottleneck evidence and expected improvement path.
- Add focused verification before broad cleanup so the optimization remains behavior-safe.

# Verification And Review

- Write or update tests for non-trivial behavior changes when practical. Prefer the smallest test scope that reliably catches the intended regression.
- Prefer unit-scale checks for isolated logic and integration-style checks for cross-module contracts, persistence, auth, or other workflow boundaries.
- Do not add tests for trivial formatting, pure delegation, or single-line pass-through wrappers with no decision logic.
- Name tests for the behavior and expected outcome, not only the method or function name.
- After any non-trivial code change, review `git diff` with a code-review lens focused on bugs, regressions, edge cases, tests, API or schema contracts, security risk, and maintainability risk.
- Use a second-pass review for multi-file, high-risk, ambiguous, or business-critical changes. Prefer an independent verifier when one is available.
- Final responses after code changes must state what validation and review actually ran. If something important was not verified, say so plainly and call out the remaining risk.
- Keep hooks and CI gates deterministic; do not make AI semantic review a mandatory blocking git hook.

# Git Safety Rails

- Prefer small, focused commits. Do not stage unrelated files with blanket `git add .` when the worktree contains mixed changes.
- When drafting a commit message, use an imperative subject line and add a body only when the why is non-obvious.
- Do not force-push shared or integration branches unless the user explicitly asks and the branch ownership makes it safe.

# Skill Routing Defaults

- At the start of any substantive new conversation, prefer `using-superpowers` as the lightweight top-level operating style.
- If the first problem is choosing the workflow shape, use `project-orchestration`. If the user only wants a plan, use `writing-plans`. If the task is clearly a phased migration or compatibility-sensitive refactor, use `large-refactor`.
- Use `parallel-execution` when the main decision is whether clearly independent workstreams are safe to split. Keep `project-orchestration` as the higher-level router for multi-phase or cross-stream coordination.
- When `paseo` is available in the current client integration and provider contrast or bounded advisory work would materially reduce risk, prefer `paseo-advisor` for read-only second opinions, use `paseo-committee` for hard planning or root-cause tradeoffs that need contrasting analyses, and use `paseo-handoff` or `paseo-loop` only after the write boundary is stable.
- When a repository task is materially underspecified, terminology-heavy, or likely to drift without alignment, use `clarify-with-repo-context`.
- For retrieval-first repository questions, use `fast-codebase-retrieval`.
- For brownfield ownership, definitions, references, implementations, call chains, or dependency wiring, use `serena-workflow` or a narrower language-specific symbolic skill.
- For product-style frontend implementation, redesign, polish, or responsive fixes, use `frontend-design`; pair with `frontend-ui-engineering` when component logic, shared UI patterns, or interaction architecture are substantial.
- For Java or Spring Boot feature work, debugging, schema changes, security, testing, or dependency management, use `java-spring-workflow`; pair with `serena-workflow` when brownfield symbol tracing matters.
- For bug reports, failing tests, build failures, or unclear behavior, use `systematic-debugging`.
- For testable behavior changes, prefer `test-driven-development`.
- For optimization, improvement, or refactor requests with an unclear or mixed axis, start with `code-optimization`. If the axis is already clearly maintainability and the work is mainly about reuse, cohesion, file health, or file boundaries, go directly to `code-maintainability`.
- When reuse, cohesion, abstraction boundaries, or file health are materially at risk, pair non-trivial implementation or review work with `code-maintainability`; escalate to `architecture-deepening` when ownership entropy, file bloat, or shallow wrappers become the main risk.
- For commit message drafting or staged change review, use `git-commit`.
- For addressing GitHub PR review comments or fixing failing GitHub Actions checks, use `gh-address-comments` or `gh-fix-ci`.
- Use `code-review` for a final second-pass review, and `security-review` when security is the primary concern.
- Use `agents-self-evolution` for durable rules, docs, glossary, memory, or workflow updates.
