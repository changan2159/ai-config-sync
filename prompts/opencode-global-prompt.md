# OpenCode-Specific Additions

- In OpenCode, prefer repository-local `AGENTS.md`, project docs, and any active memory or MCP context according to their scope.
- Treat the shared routing defaults as baseline; `AGENTS.md` or explicit user instructions can narrow, override, or forbid specific agents.
- All shared skill routing defaults apply; in OpenCode, invoke skills as `skill-<name>` in the chat (e.g., `skill-systematic-debugging`, `skill-git-commit`). This repository manages that canonical mapping in `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md`.
- For brownfield symbol navigation, definitions, or cross-file ownership, prefer `skill-serena-workflow`; for broad codebase structure and retrieval, prefer `skill-fast-codebase-retrieval`.
- Serena, CodeGraph, fetch, and node_repl are available as MCP tools in OpenCode sessions; use them directly when a task calls for live symbol lookup, document fetch, or quick JS validation rather than relying on memory alone. OpenCode has no dedicated session memory store — Serena project memory (written via Serena tools) is the primary cross-session context mechanism; write important code-structural findings there rather than assuming they will be recoverable from AGENTS.md alone.
- After completing non-trivial changes, prefer `skill-code-review` as the default second-pass review path unless a stronger OpenCode-native verifier or explicitly requested review flow should take precedence.
