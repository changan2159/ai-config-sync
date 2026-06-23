## Pi-Specific Notes

- Shared skills are synced into `~/.pi/agent/skills-shared` and loaded through `~/.pi/agent/settings.json`.
- Shared MCP servers are synced into `~/.config/mcp/mcp.json` and exposed through the installed `pi-mcp-adapter` package. Available servers: `serena`, `codegraph`, `fetch`, `node_repl`.
- Prefer the shared synced skills and MCP tools before inventing duplicate local workflows.
- Restart `pi` or run `/reload` after changing synced prompt, settings, or project skill files.
- Project-local `AGENTS.md` or explicit user instructions take precedence over the shared routing defaults; follow them when they narrow or override a skill.

## Pi-Specific Capabilities

- `pi-subagents` is available for task delegation; use it the same way `codex-subagent` is used in Codex — for bounded subtasks with clear read/write separation or parallel verification scope.
- `pi-plan-mode` provides a dedicated planning surface; activate it for large features or cross-module work before implementation, as an alternative to the `writing-plans` skill.
- `pi-nano-context` manages context window pressure; rely on it when sessions grow long rather than manually summarizing or restarting.
