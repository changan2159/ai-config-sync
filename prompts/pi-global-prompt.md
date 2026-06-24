## Pi-Specific Notes

- Shared skills are synced into `~/.pi/agent/skills-shared` and loaded through `~/.pi/agent/settings.json`.
- Shared MCP servers are synced into `~/.config/mcp/mcp.json` and exposed through the installed `pi-mcp-adapter` package. Available servers: `serena`, `codegraph`, `fetch`, `node_repl`.
- Prefer the shared synced skills and MCP tools before inventing duplicate local workflows.
- When the shared routing guidance names a skill such as `systematic-debugging`, `frontend-design`, or `code-review`, use the synced shared skill first unless the task specifically needs a Pi-only capability surface.
- Direct skill invocation uses `/skill:<name>`, and this repository manages `enableSkillCommands` in Pi settings so those commands stay available after sync. Follow `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md` for the managed cross-client mapping instead of inventing OpenCode-style `skill-...` aliases.
- Restart `pi` or run `/reload` after changing synced prompt, settings, or project skill files.
- Project-local `AGENTS.md` or explicit user instructions take precedence over the shared routing defaults; follow them when they narrow or override a skill.

## Pi-Specific Capabilities

- `pi-subagents` is available for task delegation; use it the same way `codex-subagent` is used in Codex — for bounded subtasks with clear read/write separation or parallel verification scope.
- `pi-plan-mode` provides a dedicated planning surface; activate it for large features or cross-module work before implementation, as an alternative to the `writing-plans` skill.
- `pi-nano-context` manages context window pressure; rely on it when sessions grow long rather than manually summarizing or restarting.

## Pi Routing Mappings

- Map shared routing guidance to Pi-native surfaces explicitly instead of relying on loose analogy.
- `writing-plans` maps to `pi-plan-mode` when the task needs a dedicated planning phase.
- `parallel-execution` skill decides whether work is safe to parallelize; when it concludes parallel work is appropriate, delegate bounded subtasks through `pi-subagents`.
- `codex-subagent` or other delegation guidance maps to `pi-subagents` when the task has a safe bounded sidecar scope.
- Long-session context pressure maps to `pi-nano-context`; use it before dropping important working context.
- After non-trivial changes, prefer the shared `code-review` skill as the default second pass; use `pi-plan-mode` or `pi-subagents` only when the real need is planning or delegation rather than review.
