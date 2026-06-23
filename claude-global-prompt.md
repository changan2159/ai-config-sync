# Claude-Specific Additions

- In Claude Code, prefer repository-local `CLAUDE.md`, project docs, and any active memory or MCP context according to their scope.
- When Serena or CodeGraph are available, follow the shared symbol-aware retrieval sequence; prefer them over broad text search for symbol-friendly languages and indexed source.
- Use the session memory store for project-specific discoveries that shouldn't bloat `CLAUDE.md`: verified CLI commands, module ownership maps, domain terminology, and correction patterns from past sessions.

# Claude Skill Routing Additions

- Treat the shared routing defaults as baseline; project-local `CLAUDE.md` or explicit user instructions can narrow, override, or forbid specific skills.
