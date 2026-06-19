# AI Config Sync

`ai-config-sync` owns shared MCP and skill distribution across:

- Codex
- Claude Code
- OpenCode

This project is intentionally separate from `serena-manager`.
`serena-manager` owns Serena process lifecycle.
`ai-config-sync` owns cross-client config sync.

## Single Source Of Truth

Shared source config:

```text
/home/admin101/projects/2026/ai-config-sync/shared-ai-config.json
```

Shared global prompt source:

```text
/home/admin101/projects/2026/ai-config-sync/shared-global-prompt.md
```

Codex-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/codex-global-prompt.md
```

Claude-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/claude-global-prompt.md
```

OpenCode-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/opencode-global-prompt.md
```

Shared skill sources:

```text
/home/admin101/.codex/skills
/home/admin101/.codex/skills/.system
```

## Commands

Sync once:

```bash
cd /home/admin101/projects/2026/ai-config-sync
.venv/bin/python -m ai_config_sync.cli sync-once
```

Run the watcher directly:

```bash
.venv/bin/python -m ai_config_sync.cli sync-watch
```

Install and start the persistent user service:

```bash
.venv/bin/python -m ai_config_sync.cli sync-service-start
```

Check or stop the service:

```bash
.venv/bin/python -m ai_config_sync.cli sync-service-status
.venv/bin/python -m ai_config_sync.cli sync-service-stop
```

Add or remove one MCP across all three clients:

```bash
.venv/bin/python -m ai_config_sync.cli mcp-add fetch --server-command /home/admin101/.local/bin/uvx --arg mcp-server-fetch
.venv/bin/python -m ai_config_sync.cli mcp-remove fetch
```

## Behavior

- Codex MCP config is merged into `/home/admin101/.codex/config.toml`
- Claude MCP config is merged into `/home/admin101/.claude.json`
- OpenCode MCP config is merged into `/home/admin101/.config/opencode/opencode.jsonc`
- Source `mcpServers.*.enabled: false` means that server is skipped for all synced targets
- Shared global prompt core is copied to every configured client prompt target
- Codex prompt is composed from the shared core plus the Codex overlay, then written to `/home/admin101/.codex/AGENTS.md`
- Claude prompt is composed from the shared core plus the Claude overlay, then written to `/home/admin101/.claude/CLAUDE.md`
- OpenCode prompt is composed from the shared core plus the OpenCode overlay, then written to `/home/admin101/.config/opencode/AGENTS.md`
- Plugin cache skills are not synced by default
- Codex and Claude skills are symlinked from the two shared core skill roots above
- OpenCode skills are rendered as `agent` entries from the same `SKILL.md` sources
- Codex sync currently supports only `stdio` MCP servers; remote MCP entries in the shared source will fail fast when a Codex target is enabled
- OpenCode keeps unrelated JSONC content and comments, but the managed `mcp` and `agent` sections are rewritten on sync
- `stdio` MCP entries must define `command`; sync now fails fast instead of writing broken Codex, Claude, or OpenCode config
- Symlinked config and prompt targets are updated in-place at their real destination instead of being replaced with regular files
- Skill sync keeps a local manifest in each managed skills directory so state-file loss can still clean up stale shared links without deleting unrelated manual symlinks
- Watch mode logs sync errors and keeps running instead of exiting on the first transient failure

## Global Prompt Config

`shared-ai-config.json` supports:

- top-level `globalPromptPath`: the shared source file to copy
- per-target `globalPromptPath`: the destination file for that client
- per-target `globalPromptAppendPath`: optional client-specific content appended after the shared core with a blank line separator

If a target has no prompt destination, prompt sync is skipped for that target while MCP and skill sync continue.
If the shared core is omitted but a target defines both `globalPromptPath` and `globalPromptAppendPath`, the target prompt is generated from that overlay alone.

## Recovery Notes

- Sync state lives at `state/sync-state.json`
- Managed skill directories also store `.ai-config-sync-managed.json`; if `state/sync-state.json` is lost, the next sync still knows which shared skill links it owns
- Prompt files from a previous sync are removed automatically when that target prompt is disabled or moved
- Atomic writes are used for synced prompts, target configs, the state file, the skill manifest, and the generated service file so an interrupted sync is less likely to leave partial output behind
