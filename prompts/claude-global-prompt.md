# Claude-Specific Additions

- In Claude Code, prefer repository-local `CLAUDE.md`, project docs, and any active memory or MCP context according to their scope.
- When Serena or CodeGraph are available, follow the shared symbol-aware retrieval sequence; prefer them over broad text search for symbol-friendly languages and indexed source.
- Use the session memory store for project-specific discoveries that shouldn't bloat `CLAUDE.md`: verified CLI commands, module ownership maps, domain terminology, and correction patterns from past sessions.
- Shared skills are synced into `~/.claude/skills`; prefer those shared skills before rebuilding the same workflow ad hoc in free-form reasoning.
- When a task clearly matches a shared skill, use that skill directly and keep the surrounding response focused on task-specific judgment rather than re-explaining the whole procedure.
- Direct skill invocation uses Claude's `/` command surface and `/<name>` skill form; for the managed cross-client mapping and source references, follow `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md` rather than inventing OpenCode-style `skill-...` aliases.

# Claude Skill Routing Additions

- Treat the shared routing defaults as baseline; project-local `CLAUDE.md` or explicit user instructions can narrow, override, or forbid specific skills.
- After non-trivial changes, run the shared `code-review` skill or another equivalent second-pass review path before final delivery.
