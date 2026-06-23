# Codex-Specific Additions

- When referencing local files in responses, prefer Markdown links so the user can click them in the Codex chat UI.
- When a client-specific line number format matters, prefer standard file references such as `[file.cs](/repo/src/file.cs):120` or `[file.cs](/repo/src/file.cs#L120)`.
- When Serena is available, prefer it for brownfield codebase navigation in symbol-friendly languages (C#, TypeScript, Java, Python, Go, and similar LSP-friendly languages) where cross-file tracing, declaration/reference lookup, ownership discovery, and call-chain inspection add value over text search.
- When CodeGraph is available, use it as a fast candidate-discovery layer for indexed source code: project structure, related symbols, likely owner files, callers/callees, and impact sets. Treat it as a discovery index, not the final source of truth; confirm edit targets with Serena or direct reads before changing code. Expect manual `codegraph sync` in sessions where watch is intentionally disabled.
- Default retrieval sequence when both Serena and CodeGraph are available: start with CodeGraph for anchored candidate discovery, switch to Serena to confirm owners/symbols/call chains, and use `rg` for strings, config keys, routes, JSON fields, SQL, logs, and non-indexed assets. For implementation work, do not edit from CodeGraph output alone. When the main ask is retrieval or structure understanding, prefer `fast-codebase-retrieval` as the default skill path.
- For Linux-hosted Codex sessions on this machine, follow the approved Serena and `.NET` environment workflow in `/home/admin101/.codex/rules/linux-serena-dotnet-host-notes.md`. These host notes are validated on the current Ubuntu machine and should be re-checked before copying distro-specific paths to another Linux host. If Serena disappears or `.NET` tooling drifts, repair that environment instead of inventing alternate paths.
- If a repository uses `.NET` or EF Core, follow `/home/admin101/.codex/rules/dotnet-workflow-defaults.md` for CLI tool, restore, and migration defaults instead of improvising per-project behavior.
- For persistent Codex work, prefer repository-local `AGENTS.md`, project docs, and Serena memories for durable context according to their scope.

# Codex Skill Routing Additions

- Treat the shared routing defaults as baseline; repository-local `AGENTS.md` or explicit user instructions can narrow, override, or forbid specific skills.
- Prefer the `Product Design` plugin flow only when the user explicitly invokes that plugin, or when the task is design-first rather than code-first: visual ideation, prototype exploration, URL cloning, screenshot or Figma matching, image-to-code work, flow audit, or brief-led concept exploration.
- For deciding whether to delegate a bounded subtask and writing well-scoped delegation prompts, prefer `codex-subagent`; proactively consider delegation when a task has clear read/write separation, parallel verification opportunities, or scope that would bloat the main thread.

# Codex Verification Additions

- When a child verifier agent is available, prefer it as the first-pass independent reviewer before reaching for the `code-review` skill or a manual diff.
