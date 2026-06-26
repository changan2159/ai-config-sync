## Pi-Specific Notes

- Shared skills are synced into `~/.pi/agent/skills-shared` and loaded through `~/.pi/agent/settings.json`.
- Shared MCP servers are synced into `~/.config/mcp/mcp.json` and exposed through the installed `pi-mcp-adapter` package. Available servers: `serena`, `codegraph`, `fetch`, `node_repl`.
- Prefer the shared synced skills and MCP tools before inventing duplicate local workflows.
- Prefer the direct Pi tools registered from `serena`, `codegraph`, `fetch`, and `node_repl` when they are available. The generic MCP proxy tool is intentionally hidden from the default Pi tool list once direct-tool metadata is ready.
- When the shared routing guidance names a skill such as `systematic-debugging`, `frontend-design`, or `code-review`, proactively load the synced shared skill first unless the task specifically needs a Pi-only capability surface.
- For substantive repository tasks, do an explicit routing pass before acting: choose the best matching shared skill and the best retrieval surface rather than starting with broad shell search by default.
- Direct skill invocation uses `/skill:<name>`, and this repository manages `enableSkillCommands` in Pi settings so those commands stay available after sync. Follow `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md` for the managed cross-client mapping instead of inventing OpenCode-style `skill-...` aliases.
- Restart `pi` or run `/reload` after changing synced prompt, settings, or project skill files.
- Project-local `AGENTS.md` or explicit user instructions take precedence over the shared routing defaults; follow them when they narrow or override a skill.

## Pi-Specific Capabilities

- `pi-subagents` is available for task delegation; use it the same way `codex-subagent` is used in Codex — for bounded subtasks with clear read/write separation or parallel verification scope.
- `pi-plan-mode` provides a dedicated planning surface; activate it for large features or cross-module work before implementation, as an alternative to the `writing-plans` skill.
- `pi-goal` is available for persistent long-running objectives; use it for substantial end-to-end implementation goals instead of relying only on conversational continuity.
- `pi-context-prune` is installed and should be treated as the default context-compaction path for long sessions.
- `pi-context-usage` and `pi-cache-graph` are available for observability when you need to inspect context growth or cache behavior.
- `pi-fallback-provider` is installed for model failover; prefer the configured fallback chain over asking the user to switch models manually for transient provider failures.
- `pi-autonomy-orchestrator` is a Pi-only repo skill that activates all Pi-native runtime surfaces automatically during substantial development work; load it at the start of any multi-turn task where goal persistence, context compaction, or delegation is expected to matter.

## Pi Routing Mappings

- Map shared routing guidance to Pi-native surfaces explicitly instead of relying on loose analogy.
- For repo structure, ownership, call-chain, and related-file questions, start with `fast-codebase-retrieval` plus direct `codegraph` and/or `serena` tools before broad text-only search.
- For brownfield code changes where definitions, references, or dependency wiring matter, load `serena-workflow` early and use the direct `serena` tools as the primary navigation surface.
- For external docs, API references, or version-sensitive facts, prefer the direct `fetch` tool instead of memory-based answers.
- If a request clearly matches a shared skill, load that skill before continuing; do not wait for the user to explicitly name it when the routing guidance already fits.
- `writing-plans` maps to `pi-plan-mode` when the task needs a dedicated planning phase.
- `project-orchestration` for substantial Pi work should consider `pi-goal` as the default persistence surface once the objective is concrete and multi-turn.
- `parallel-execution` skill decides whether work is safe to parallelize; when it concludes parallel work is appropriate, delegate bounded subtasks through `pi-subagents`.
- `codex-subagent` or other delegation guidance maps to `pi-subagents` when the task has a safe bounded sidecar scope.
- Long-session context pressure maps first to `pi-context-prune`, then to `pi-context-usage` or `pi-cache-graph` for diagnosis; prefer those over adding UI-only context meters back into the default stack.
- After non-trivial changes, prefer the shared `code-review` skill as the default second pass; use `pi-plan-mode` or `pi-subagents` only when the real need is planning or delegation rather than review.
- When Pi is configured with fallback model chains, treat those chains as the first line of resilience for retryable provider failures.
- For substantial multi-turn tasks, load `/skill:pi-autonomy-orchestrator` early; it activates Pi-native goal, plan, prune, fallback, and delegation surfaces automatically so they are ready before context or model pressure arises.
