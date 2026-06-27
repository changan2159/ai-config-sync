# OpenCode-Specific Additions

- In OpenCode, prefer repository-local `AGENTS.md`, project docs, and any active memory or MCP context according to their scope.
- Invoke shared skills as `skill-<name>` in the chat, for example `skill-systematic-debugging`, `skill-fast-codebase-retrieval`, or `skill-serena-workflow`.
- This repository manages the canonical mapping in `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md`; do not invent alternate aliases.
- Serena, CodeGraph, `fetch`, and `node_repl` are available in OpenCode sessions; use them directly when the task calls for live retrieval, docs lookup, or quick JavaScript validation.
- Serena project memory is the primary cross-session context mechanism in OpenCode; write important code-structural discoveries there instead of assuming they will remain recoverable from chat history alone.
- Treat the shared routing defaults as the baseline; `AGENTS.md` and explicit user instructions can narrow or override them.
- After non-trivial changes, prefer `skill-code-review` as the default second-pass review path unless a stronger OpenCode-native verifier is available.
