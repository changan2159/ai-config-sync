# Codex-Specific Additions

- When referencing local files in responses, prefer Markdown links so the user can click them in the Codex chat UI.
- When a client-specific line number format matters, prefer standard file references such as `[file.cs](/repo/src/file.cs):120` or `[file.cs](/repo/src/file.cs#L120)`.
- When Serena is available, prefer it for brownfield codebase navigation in symbol-friendly languages (C#, TypeScript, Java, Python, Go, and similar LSP-friendly languages) where cross-file tracing, declaration/reference lookup, ownership discovery, and call-chain inspection add value over text search.
- When CodeGraph is available, use it as a fast candidate-discovery layer for indexed source code: project structure, related symbols, likely owner files, callers/callees, and impact sets. Treat it as a discovery index, not the final source of truth; confirm edit targets with Serena or direct reads before changing code. Expect manual `codegraph sync` in sessions where watch is intentionally disabled.
- Default retrieval sequence when both Serena and CodeGraph are available: start with CodeGraph for anchored candidate discovery, switch to Serena to confirm owners/symbols/call chains, and use `rg` for strings, config keys, routes, JSON fields, SQL, logs, and non-indexed assets. For implementation work, do not edit from CodeGraph output alone. When the main ask is retrieval or structure understanding, prefer `fast-codebase-retrieval` as the default skill path.
- For persistent Codex work, prefer repository-local `AGENTS.md`, project docs, and Serena memories for durable context according to their scope.

# Codex Skill Routing Additions

- Treat the shared routing defaults as baseline; repository-local `AGENTS.md` or explicit user instructions can narrow, override, or forbid specific skills.
- Prefer the `Product Design` plugin flow only when the user explicitly invokes that plugin, or when the task is design-first rather than code-first: visual ideation, prototype exploration, URL cloning, screenshot or Figma matching, image-to-code work, flow audit, or brief-led concept exploration.
- For deciding whether to delegate a bounded subtask and writing well-scoped delegation prompts, prefer `codex-subagent`; proactively consider delegation when a task has clear read/write separation, parallel verification opportunities, or scope that would bloat the main thread.

# Codex Verification Additions

- When a child verifier agent is available, prefer it as the first-pass independent reviewer before reaching for the `code-review` skill or a manual diff.

# Codex Review Commands

- Prefer the child verifier path first; if that is unavailable, reuse the verified non-interactive CLI commands on this host instead of improvising flags.
- `Codex CLI` native review shape: `cat /tmp/review-prompt.txt | codex review --uncommitted`
- `Claude CLI` health probe when reliability matters: `claude -p --bare --no-session-persistence --permission-mode dontAsk --output-format json "Reply with exactly OK."`
- `Claude CLI` substantive review shape: `cat /tmp/review-prompt.txt | claude -p --bare --no-session-persistence --permission-mode dontAsk --input-format text --output-format json`
- Treat `Claude CLI` as failed for review purposes if it exits `0` but returns an empty `result`.
- `OpenCode CLI` cross-review shape: `opencode run "$(cat /tmp/review-prompt.txt)" --format json`
- For `OpenCode CLI`, read the final review text from the emitted JSON event stream; the assistant verdict appears in the last event object with `"role": "assistant"` (or equivalent content event); do not mistake intermediate tool-call or tool-result events for the actual verdict.
