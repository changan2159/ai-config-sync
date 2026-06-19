# Serena Manager

`serena-manager` keeps one long-lived Serena MCP instance per project and exposes a stdio entrypoint that Codex can use as a drop-in replacement for direct `serena start-mcp-server --transport stdio`.

## Architecture

```text
Codex stdio client
  -> serena-manager launcher
  -> project-scoped Serena daemon (streamable-http)
  -> Roslyn / language servers
```

Key properties:

- same project reuses one Serena process
- same project reuses one Serena process across Codex, Claude Code, OpenCode, and other stdio MCP clients
- different projects stay isolated
- idle instances are reaped after 20 minutes by default
- unhealthy instances are rebuilt automatically

## Install

```bash
cd /home/admin101/.codex/mcp/serena-manager
uv sync --dev
```

## Run

Codex MCP entrypoint:

```bash
/home/admin101/.codex/mcp/serena-manager/run-serena-manager.sh
```

Operator commands:

```bash
.venv/bin/python -m serena_manager.cli status
.venv/bin/python -m serena_manager.cli doctor
.venv/bin/python -m serena_manager.cli stop --project /path/to/repo
.venv/bin/python -m serena_manager.cli cleanup
.venv/bin/python -m serena_manager.cli reap --once
```

## State

Runtime state lives under:

```text
/home/admin101/.codex/mcp/serena-manager/state/<project-hash>/
```

Each project directory contains:

- `meta.json`
- `lock`
- `manager.log`
- `serena.stdout.log`
- `serena.stderr.log`

## Codex Config

Linux Codex config should point `mcp_servers.serena.command` to:

```text
/home/admin101/.codex/mcp/serena-manager/run-serena-manager.sh
```

Current machine note:

- `/home/admin101/.codex/config.toml` can be updated directly for the active Linux Codex session

## Verify

```bash
.venv/bin/pytest -q
.venv/bin/python -m serena_manager.cli status
```

Expected outcomes:

- two Codex sessions in the same repo share one Serena PID
- Codex, Claude Code, and OpenCode sessions in the same repo share one Serena PID
- a different repo gets a different Serena PID
- idle instances disappear after timeout or `reap --once`

## Client Compatibility

The managed Serena daemon now starts with the neutral Serena context `desktop-app` instead of a client-specific context like `codex`.

That makes the reuse key effectively:

- same detected `project_root`
- same shared manager config

So any MCP client that launches this repository's [`run-serena-manager.sh`](/home/admin101/.codex/mcp/serena-manager/run-serena-manager.sh) can attach to the same Serena daemon for the same repository.

If an older state directory still points to a daemon started with a client-specific context such as `codex`, the manager will terminate and replace it on the next connection so future clients converge on the shared daemon.

## Rollback

Restore the previous Serena MCP command in Codex config:

```toml
command = "/home/admin101/.local/bin/uvx"
args = ["--from", "serena-agent", "serena", "start-mcp-server", "--context", "codex", "--project-from-cwd", "--enable-web-dashboard", "false", "--open-web-dashboard", "false", "--enable-gui-log-window", "false"]
```
