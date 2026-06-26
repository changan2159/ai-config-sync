# Sync Scope Audit

This file records which artifacts are currently shared across all managed clients and which are intentionally target-specific.

## Skills

### Shared Skills

Shared skills live as direct children under `skills/shared/`.
Anything placed there is considered cross-client and is synced to every target that consumes shared repo skills.

Current shared set includes (illustrative, not exhaustive — the authoritative list is the set of directories under `skills/shared/`):

- retrieval, planning, review, maintainability, debugging, frontend, accessibility, performance, release, database, document, and architecture skills
- framework- or domain-specific skills such as `aspnet-core`, `csharp-symbolic-workflow`, and `mcp-builder`

### Target-Specific Skills

- Codex only: `codex-subagent`
  - reason: the skill contains Codex CLI delegation mechanics and `codex exec` command shapes
  - location: `skills/codex/codex-subagent/`
  - sync policy: only the Codex target adds `skillRoots: [{"path": "${REPO_ROOT}/skills/codex"}]`
- Pi only: repo skills under `skills/pi/`
  - reason: these skills map shared workflows onto Pi-native capability surfaces
  - location: `skills/pi/`
  - sync policy: only the Pi target adds `skillRoots: [{"path": "${REPO_ROOT}/skills/pi"}]`

## MCP Servers

### Shared MCP

These are currently shared across all managed clients:

- `fetch`
- `serena`
- `node_repl`
- `codegraph`

reason:

- each server is configured through the shared source config
- each managed client in this repository has a supported way to consume stdio MCP servers
- no current server is coupled to a single client's invocation semantics

### Target-Specific MCP

None today.

Shared MCP wrappers belong under `tools/mcp/shared/`.
If a future server becomes client-specific, put its wrapper under `tools/mcp/<client>/` and register it through that target's `mcpServers` block instead of adding filter rules.

## Prompt And Docs

### Shared

- `prompts/shared-global-prompt.md`
- `docs/shared/agent-integration.md`
- `docs/shared/runtime/linux-serena-dotnet-host-notes.md`
- `docs/shared/workflows/dotnet-workflow-defaults.md`

### Target-Specific

- `prompts/codex-global-prompt.md`
- `prompts/claude-global-prompt.md`
- `prompts/opencode-global-prompt.md`
- `prompts/pi-global-prompt.md`

reason:

- overlays describe invocation syntax, review entry points, and client-native capability surfaces that differ by target
- future client-specific docs should live under `docs/<client>/`

## Pi Packages

Pi-only managed packages remain target-specific:

- `npm:pi-mcp-adapter`
- `npm:@narumitw/pi-plan-mode`
- `npm:pi-subagents`
- `npm:pi-goal`
- `npm:pi-context-prune`
- `npm:pi-context-usage`
- `npm:pi-cache-graph`
- `npm:pi-fallback-provider`

These are not mirrored to other clients because they are Pi runtime extensions rather than portable shared skills.
