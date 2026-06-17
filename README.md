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
- Codex and Claude skills are symlinked to the shared source skill folders
- OpenCode skills are rendered as `agent` entries from the same `SKILL.md` sources
