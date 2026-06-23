# Claude-Specific Additions

- In Claude Code, prefer repository-local `CLAUDE.md`, project docs, and any active memory or MCP context according to their scope.
- When Serena or CodeGraph are available, follow the shared symbol-aware retrieval sequence; prefer them over broad text search for symbol-friendly languages and indexed source.

# Claude Skill Routing Additions

- Treat the shared routing defaults as baseline; project-local `CLAUDE.md` or explicit user instructions can narrow, override, or forbid specific skills.
- When symbol confirmation matters alongside implementation location lookups, pair `fast-codebase-retrieval` with `serena-workflow` for cross-file verification.
