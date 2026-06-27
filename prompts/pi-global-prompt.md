## Pi-Specific Additions

- Shared skills are synced into `~/.pi/agent/skills-shared` and loaded through `~/.pi/agent/settings.json`.
- Shared MCP servers are synced into `~/.config/mcp/mcp.json` and exposed through the installed `pi-mcp-adapter` package.
- Prefer the direct Pi tools registered from `serena`, `codegraph`, `fetch`, and `node_repl` when they are available. The generic MCP proxy tool is intentionally hidden once direct-tool metadata is ready.
- For brownfield retrieval, start with direct `codegraph` / `serena` tools before broad text search, following the shared retrieval default.
- Pi-native packages available in this managed setup include `pi-plan-mode` for dedicated planning, `pi-subagents` for bounded delegation, `pi-goal` for persistent objectives, `pi-context-prune` for compaction, `pi-context-usage` and `pi-cache-graph` for diagnostics, and `pi-fallback-provider` for model failover.
- Invoke shared skills with `/skill:<name>`.
- If a request clearly matches a shared skill, load it before continuing rather than waiting for the user to name it explicitly.
- For canonical shared skill names and cross-client mapping details, follow `/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md`.
- After changing synced prompts, settings, or repo skill files, run `/reload` or restart `pi`.
- Project-local `AGENTS.md` and explicit user instructions override the shared defaults.

## Pi-Native Workflow

- For substantial multi-turn work, load `/skill:pi-autonomy-orchestrator` early so Pi-native goal, plan, prune, fallback, and delegation surfaces are ready before they are needed.
- Map native surfaces by need, not novelty: keep retrieval on shared tools first, then activate Pi-native planning, persistence, delegation, or compaction surfaces only when that is the real next need.
- Shared-route crosswalk: `writing-plans` maps to `pi-plan-mode`; persistent multi-turn `project-orchestration` work can use `pi-goal`; `parallel-execution` and bounded delegation map to `pi-subagents`; long-session context pressure maps first to `pi-context-prune`, then to `pi-context-usage` or `pi-cache-graph`.
- Use `pi-plan-mode` when the main need is a dedicated planning surface.
- Use `pi-subagents` only for bounded delegation or independent verification after the write boundary is stable.
- Use `pi-goal` only when the objective is concrete, multi-turn, and worth persistent tracking.
- Use `pi-context-prune` first for long-session compaction; use `pi-context-usage` or `pi-cache-graph` only when you need to diagnose context growth.
- Prefer configured `pi-fallback-provider` chains for transient model or provider failures instead of asking the user to switch models manually.
