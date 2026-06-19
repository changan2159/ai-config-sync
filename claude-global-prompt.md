# Claude-Specific Additions

- In Claude Code, prefer repository-local `CLAUDE.md`, project docs, and any active memory or MCP context according to their scope.
- When synced MCP tools such as `serena` or `codegraph` are available in Claude, use them to realize the shared symbol-aware and graph-assisted retrieval workflow rather than falling back too early to broad text search.
- When synced skills or focused workflows are available in Claude, prefer the task-specific path that best matches debugging, repository retrieval, review, frontend work, or durable context updates.
- For second-pass verification in Claude, prefer an independent read-only reviewer path when available before relying only on a manual diff read.
