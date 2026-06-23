# Shared Core Preferences

- Prefer concise, client-friendly file references. When the client supports clickable Markdown file links, use them; otherwise include the plain absolute path.
- Use absolute filesystem paths when pointing to local files.
- When a line number is useful, prefer standard file references such as `[file.cs](/repo/src/file.cs):120` or `[file.cs](/repo/src/file.cs#L120)`.
- If both a Markdown link and a plain path are useful, provide the richer reference first.
- Repository-local instruction files, project docs, and verified project scripts override these global defaults when they conflict. Use this file for cross-project collaboration defaults, not project-specific policy.
- Avoid redundant historical cleanup commentary in responses. If obsolete paths or rules have already been removed, do not spend answer space stating that they are no longer used unless that fact is operationally necessary.
- Avoid trailing punctuation directly after a Markdown file link when possible.
- Decide autonomously when a task is suitable for parallel execution.
- Explore first, then parallelize: use a short serial pass to identify the critical path, write boundaries, and blockers before splitting work.
- Prefer parallel execution for information gathering, code reading, independent verification, and edits in clearly non-overlapping modules.
- Keep mainline implementation serial until the owning file or module and interface seam are stable; only parallelize writes after that boundary is clear.
- Switch to serial execution when tasks write to the same file or module, have strong ordering dependencies, rely on unstable interfaces, or when one result directly determines another implementation.
- Keep ownership explicit and avoid duplicated analysis, duplicated edits, or conflicting changes.
- Default to UTF-8 for documentation, scripts, templates, AI-maintained context, terminal output, and generated text files.
- Do not rely on GBK/CP936 defaults unless a legacy file or external system explicitly requires that encoding; document the exception near the command or file.
- In Python, pass `encoding="utf-8"` when reading or writing text files.
- When symbol-aware navigation is available, prefer it for brownfield codebase work where declarations, references, call chains, ownership, or cross-file structure matter more than raw string search.
- When an indexed code graph or discovery tool is available, use it as a candidate-discovery layer for likely owner files, callers, callees, and impact sets; confirm edit targets with symbol-aware tools or direct reads before changing code.
- A good default retrieval sequence is: graph/index discovery first when available, symbol-aware confirmation second, and plain text search for config keys, routes, JSON fields, SQL, logs, docs, and other string-driven behavior.
- Do not force symbol-aware tools for weak-symbol or poorly indexed codebases, simple single-file edits, build or test execution, or small frontend styling changes where symbolic navigation adds little value.
- When querying a code graph or index, prefer explicit symbol names, file stems, endpoint paths, or DTO names as anchors over broad natural-language queries; tighten noisy results with concrete identifiers before broadening the query.
- When `fetch` is available, use it for documentation lookups, external API references, or changelog reading rather than relying on training-data recall for version-sensitive details.
- When `node_repl` is available, use it as a quick scratchpad for validating JavaScript snippets, arithmetic, or data transforms without creating temporary files.
- When specialized workflows, skills, or agents are available for a task shape such as debugging, code review, frontend work, context persistence, or repository retrieval, prefer those focused paths over an unfocused general pass.
- After any non-trivial coding, debugging, review, or refactor task, do a brief self-check for durable context worth preserving. If stable project structure, business rules, verified commands, terminology, or repeated corrections were discovered, persist them in the narrowest correct place instead of waiting for the user to ask again.
- Persist only knowledge that is likely to matter again across future tasks. Keep stable defaults in shared guidance, shared project facts in project docs, and machine-specific or more volatile observations in dedicated notes or a memory store.
- Do not update the global instruction file for one-off troubleshooting notes, temporary workarounds, or unverified guesses. Put volatile observations in a narrower note or memory store until they are proven durable.
- Treat end-of-task context persistence as a standing obligation for non-trivial tasks, not an optional step: classify any reusable understanding discovered, write it to the narrowest correct location, downgrade weak inferences to open questions, and surface only meaningful updates in the final response.

# Brownfield Architecture Check

- Treat work as non-trivial when any of these are true: it crosses files, changes a public or shared interface, touches persistence, auth, billing, or state-transition behavior, changes user-visible workflow or contract, or requires adding or updating tests. Single-file local edits with no shared contract change can stay on the lightweight path.
- For non-trivial development in existing code, run a lightweight owner/seam check before editing:
  - what concept is changing
  - which existing file/module currently owns it
  - whether the current owner should absorb the change or a clearer domain-shaped seam should emerge
  - whether callers are doing work that should move behind that owner/seam
- Keep this pre-code pass short by default. Do not turn every feature task into a long architecture report.
- Escalate into a stronger architecture-deepening lens when the main risk becomes structural entropy rather than only correctness or delivery:
  - a file keeps growing without becoming more cohesive
  - new helpers or services are mostly pass-through wrappers, renames, or parameter plumbing
  - orchestration, mapping, validation, or permission logic repeats across callers
  - understanding one behavior requires jumping through many thin files
- For tiny or low-risk local edits, the architecture check can stay implicit and brief.

# UI Design Preferences

- Apply this section only to product-style frontend work with a real user interface. Do not project these UI preferences onto backend-only repos, CLI tools, libraries, scripts, or documentation-only work.
- Product UI should make one primary task obvious per screen or work area. Secondary metadata, explanations, filters, and diagnostics must not receive the same visual weight as the main action or editing surface.
- Titles, option labels, rule labels, table headers, and inline descriptions should be concise. If users may need more context, use a small help/question icon, tooltip, popover, drawer, or progressive-disclosure panel instead of placing long explanatory text directly in the main layout.
- Preserve the user's space budget. Avoid large decorative headers, repeated context blocks, oversized cards, and explanatory chrome that forces simple operational screens to scroll before the user can act.
- Prefer user-intent templates, guided controls, examples, and visual grouping over raw JSON, raw expressions, protocol paths, internal keys, or code-like configuration as the primary editing experience. Raw/technical editing can exist, but should be an advanced mode.
- Do not ask users to manually fill technical identifiers such as unique keys, slugs, internal IDs, sort indexes, or linkage fields unless they are genuinely required for user-facing semantics, interoperability, or external integration. Prefer generated IDs, derived identifiers, or hidden internal linkage.
- Hide optional technical/debug fields behind advanced settings. When technical fields are required, explain why in one concise sentence or tooltip, not as persistent long-form text.
- Keep editing, validation feedback, and preview close together. If a user changes a rule, form, transformation, or visual setting, the effect or next-step error should be visible in the same work area without searching elsewhere.
- For repeated operational data, prefer dense, scannable tables/lists with a focused inspector, drawer, or detail pane. Avoid repeating full explanations, forms, or large cards for every row.
- Status labels should distinguish cause and next action. Use short inline wording for common states and move detailed reasoning into hover/focus tips or expandable diagnostics.
- Responsive UI must preserve task priority, not merely stack everything. On smaller screens, keep primary controls reachable, collapse secondary context first, and avoid horizontal overflow.
- Use visual polish to clarify hierarchy and workflow, not to decorate empty space. Color, typography, borders, shadows, motion, and illustrations should help users scan, decide, or act.

# Code Review and Verification

- After any non-trivial code change, review `git diff` in a code-review style before final delivery. Focus on bugs, regressions, missed requirements, edge cases, test coverage, API contracts, security risk, and maintainability risk.
- For moderately complex or higher changes, default to a second-pass review. Prefer an independent verifier or reviewer first when available, and fall back to a stricter manual diff review only when no independent verification path is available.
- For cross-review with another coding assistant or CLI, feed a fixed commit or exported patch plus the smallest relevant surrounding context (callers, callees, tests, and config). Do not rely on raw diff alone for cross-module or behavioral changes, and keep the reviewer read-only.
- Always use a second-pass review for multi-file changes, high-risk changes, ambiguous requirements, cross-module contract changes, and permission, money, order, or business state-transition logic.
- Small single-file edits may skip a second-pass verifier, but still require reading the diff and running the smallest relevant validation.
- Hooks should only run deterministic checks such as lint, typecheck, format check, unit tests, secret scanning, or debug-log prevention. Do not make AI semantic review a mandatory git hook.
- Final responses after code changes must state what validation actually ran. If tests or review were skipped, state why and call out the remaining risk.

# Cross-CLI Review Invocation

- Reuse these verified non-interactive CLI shapes for read-only review instead of improvising new flag combinations each time.
- `Codex CLI`: pass review instructions through stdin to `codex review --uncommitted`.
  Example:
  ```bash
  cat /tmp/review-prompt.txt | codex review --uncommitted
  ```
- `Claude CLI`: first use a short health probe when reliability matters.
  Example:
  ```bash
  claude -p --bare --no-session-persistence --permission-mode dontAsk --output-format json "Reply with exactly OK."
  ```
- `Claude CLI`: for substantive review prompts, prefer stdin plus explicit JSON output.
  Example:
  ```bash
  cat /tmp/review-prompt.txt | claude -p --bare --no-session-persistence --permission-mode dontAsk --input-format text --output-format json
  ```
- Treat `Claude CLI` as failed for review purposes if it exits `0` but returns an empty `result`; do not count that as a completed review.
- `OpenCode CLI`: use `opencode run` with `--format json` for non-interactive review prompts.
  Example:
  ```bash
  opencode run "$(cat /tmp/review-prompt.txt)" --format json
  ```
- For `OpenCode CLI`, read the final review text from the emitted JSON event stream; do not mistake intermediate tool dumps for the actual verdict.

# Testing

- Write tests for non-trivial behavior changes; prefer the smallest test scope that reliably catches the intended regression.
- Prefer unit tests for isolated logic; use integration tests for cross-module contracts, persistence, auth, and external services.
- Do not add tests for trivial delegation, pure formatting, or single-line wrappers with no decision logic.
- Test names should state what is being tested and what the expected outcome is, not just the method name.

# Git and Commits

- Prefer small, focused commits. One logical change per commit; avoid bundling unrelated fixes or refactors.
- Commit message: imperative mood, concise subject line; add a body when the why is non-obvious.
- Do not force-push shared or integration branches; use a new commit to revise published history.
- Stage and review changes before committing; avoid blanket `git add .` when unrelated files are present.

# Skill Routing Defaults

- Treat these as default routing hints; project-local instruction files and explicit user instructions can narrow, override, or forbid specific skills.
- At the start of any substantive new conversation, prefer `using-superpowers` to establish the default operating mode before the first task.
- When a request is underspecified or scope is ambiguous, prefer `clarify-with-repo-context` rather than proceeding on assumptions.
- For large features, migrations, or cross-module work where the approach is not yet settled, prefer `writing-plans` before coding.
- For bug reports, failing tests, build breaks, or reproduced-but-unexplained behavior, prefer `systematic-debugging`.
- For production behavior changes where tests are practical, prefer `test-driven-development`.
- For finding implementation locations, related files, call chains, or project structure, prefer `fast-codebase-retrieval`; pair with `serena-workflow` when symbol confirmation or cross-file ownership matters.
- For non-trivial brownfield work in symbol-friendly languages (C#, TypeScript, Java, Python, Go), prefer `serena-workflow` to anchor navigation before broad text-only exploration.
- For C# or .NET-specific symbol tracing, call-chain inspection, and type navigation, prefer `csharp-symbolic-workflow` over generic text search or broad Serena queries.
- For rule, docs, memory, glossary, or durable-context updates, prefer `agents-self-evolution`.
- For code review or second-pass verification, prefer `code-review`; use `security-review` when security is the primary concern.
- For product-style frontend implementation, redesign, polish, or responsive fixes, prefer `frontend-design`; pair with `frontend-ui-engineering` when component logic or shared UI architecture is substantial.
- For non-trivial brownfield work with growing structural risk, prefer `architecture-deepening`.
- For multi-file, cross-module restructuring that needs sequencing and ownership mapping, prefer `large-refactor`.
- For commit message drafting and staged change review, prefer `git-commit`.
- For addressing GitHub PR review comments or fixing CI failures, prefer `gh-address-comments` or `gh-fix-ci` respectively.
- For tasks that decompose into clearly independent workstreams, prefer `parallel-execution`; for multi-phase deliverables requiring cross-stream coordination, prefer `project-orchestration`.
