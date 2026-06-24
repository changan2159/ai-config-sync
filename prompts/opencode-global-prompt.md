# OpenCode-Specific Additions

- In OpenCode, prefer repository-local `AGENTS.md`, project docs, and any active memory or MCP context according to their scope.
- When Serena or CodeGraph are available, follow the shared symbol-aware retrieval sequence; prefer them over broad text search for symbol-friendly languages and indexed source.
- Treat the shared routing defaults as baseline; `AGENTS.md` or explicit user instructions can narrow, override, or forbid specific agents.
- All shared skill routing defaults apply; in OpenCode, invoke skills as `skill-<name>` in the chat (e.g., `skill-systematic-debugging`, `skill-git-commit`). This repository manages that canonical mapping in `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md`.
- After completing non-trivial changes, prefer `skill-code-review` as the default second-pass review path unless a stronger OpenCode-native verifier or explicitly requested review flow should take precedence.
