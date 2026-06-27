# Claude-Specific Additions

- In Claude Code, prefer repository-local `CLAUDE.md`, project docs, and any active memory or MCP context according to their scope.
- Use the session memory store for client-specific operational discoveries that should not bloat `CLAUDE.md`, and use Serena memory for code-structural knowledge such as ownership, call chains, and cross-file wiring.
- Shared skills are synced into `~/.claude/skills`; use the matching shared skill directly when the task clearly fits it.
- Invoke shared skills through Claude's `/<name>` command surface.
- For canonical shared skill names and cross-client mapping details, follow `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md` rather than inventing OpenCode-style aliases.
- Treat the shared routing defaults as the baseline; project-local `CLAUDE.md` and explicit user instructions can narrow or override them.
- After non-trivial changes, run the shared `code-review` skill or another equivalent second-pass review path before final delivery.
