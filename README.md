# AI Config Sync

`ai-config-sync` owns shared MCP and skill distribution across:

- Codex
- Claude Code
- OpenCode
- Pi

`serena-manager` is maintained directly inside this repository under `vendor/mcp/serena-manager`.
`ai-config-sync` owns the shared cross-client sync layer and the vendored MCP update entrypoints.

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

Pi-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/pi-global-prompt.md
```

Shared skill sources:

```text
/home/admin101/projects/2026/ai-config-sync/skills
```

Repo-local MCP wrappers:

```text
/home/admin101/projects/2026/ai-config-sync/tools/mcp
```

Repo-local MCP runtimes:

```text
/home/admin101/projects/2026/ai-config-sync/vendor/mcp
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

Add or remove one MCP across all four clients:

```bash
.venv/bin/python -m ai_config_sync.cli mcp-add fetch --server-command "${PWD}/tools/mcp/fetch.sh"
.venv/bin/python -m ai_config_sync.cli mcp-remove fetch
```

Install Pi and the MCP adapter package:

```bash
npm install -g --ignore-scripts --prefix "$HOME/.local" @earendil-works/pi-coding-agent
pi install npm:pi-mcp-adapter
pi --version
```

Update vendored MCPs:

```bash
.venv/bin/python -m ai_config_sync.cli mcp-update-serena-agent
.venv/bin/python -m ai_config_sync.cli mcp-update-fetch
.venv/bin/python -m ai_config_sync.cli mcp-update-codegraph
.venv/bin/python -m ai_config_sync.cli mcp-update-node-repl-linux
.venv/bin/python -m ai_config_sync.cli mcp-update-all
```

Prepare the repo-local MCP toolchain and runtimes after a fresh clone, branch switch, or runtime-stale error:

```bash
.venv/bin/python -m ai_config_sync.cli mcp-preflight
```

Install or update the managed OpenCode runtime:

```bash
.venv/bin/python -m ai_config_sync.cli opencode-install
.venv/bin/python -m ai_config_sync.cli opencode-install --version 1.17.8
```

Install or start the managed OpenCode web service:

```bash
sudo .venv/bin/python -m ai_config_sync.cli opencode-service-install
sudo .venv/bin/python -m ai_config_sync.cli opencode-service-start
.venv/bin/python -m ai_config_sync.cli opencode-status
```

Update an existing managed install:

```bash
.venv/bin/python -m ai_config_sync.cli opencode-install --version 1.17.8
sudo systemctl restart opencode-web.service
```

Script entrypoints:

```bash
./scripts/claude/update-claude.sh
./scripts/claude/update-claude.sh 2.1.183
./scripts/opencode/update-opencode.sh
./scripts/opencode/update-opencode.sh 1.17.8
./update-all-mcp.sh
./scripts/mcp/update-serena-agent.sh
./scripts/mcp/update-fetch.sh
./scripts/mcp/update-codegraph.sh
./scripts/mcp/update-node-repl-linux.sh
```

## Behavior

- Codex MCP config is merged into `/home/admin101/.codex/config.toml`
- Claude MCP config is merged into `/home/admin101/.claude.json`
- OpenCode MCP config is merged into `/home/admin101/.config/opencode/opencode.jsonc`
- Pi shared MCP config is merged into `/home/admin101/.config/mcp/mcp.json`
- Shared config uses `${REPO_ROOT}` and `${HOME}` placeholders so sync follows the current checkout location and current login user instead of one hard-coded username
- Source `mcpServers.*.enabled: false` means that server is skipped for all synced targets
- Shared global prompt core is copied to every configured client prompt target
- Codex prompt is composed from the shared core plus the Codex overlay, then written to `/home/admin101/.codex/AGENTS.md`
- Claude prompt is composed from the shared core plus the Claude overlay, then written to `/home/admin101/.claude/CLAUDE.md`
- OpenCode prompt is composed from the shared core plus the OpenCode overlay, then written to `/home/admin101/.config/opencode/AGENTS.md`
- Pi prompt is composed from the shared core plus the Pi overlay, then written to `/home/admin101/.pi/agent/AGENTS.md`
- Claude should use the native user-level install under `/home/admin101/.local/bin/claude`; avoid keeping a parallel global npm install because `claude update` warns on multi-install drift and the native updater already manages versions under `/home/admin101/.local/share/claude/versions/`
- Plugin cache skills are not synced by default
- Shared skill sync only mirrors repo-local `skills/`; client-native system skills remain owned by each CLI instead of being cross-synced
- OpenCode skills are rendered as `agent` entries from the same `SKILL.md` sources
- Pi skills are symlinked into `/home/admin101/.pi/agent/skills-shared`, and `~/.pi/agent/settings.json` keeps that directory plus the managed `npm:pi-mcp-adapter` package registered
- Managed OpenCode runtime installs live under `/home/admin101/.local/share/ai-config-sync/opencode/releases/<version>` as official release binaries instead of `/usr/local/lib/node_modules`
- `/home/admin101/.local/bin/opencode` is a managed wrapper that probes `current` first and falls back to the previous healthy release if the current one is broken
- `opencode-install` resolves the latest version from the official GitHub releases API, downloads the matching release asset for the current host, validates both `opencode --version` and a short-lived `opencode serve` probe, and only then switches the `current` symlink
- The canonical boot path is the system service `/etc/systemd/system/opencode-web.service`, which runs as the login user but starts from `multi-user.target` instead of depending on a user-session service
- `opencode-service-start` disables the old user unit `opencode-web-managed.service` before enabling the system service, so future updates do not recreate the previous port-conflict path
- `loginctl linger` may still remain enabled on this host for `ai-config-sync.service`, but OpenCode itself no longer depends on a user service or linger to start after boot
- MCP commands point at repo-local wrapper scripts under `tools/mcp/`, and those wrappers bootstrap only the vendored repo-local runtimes under `vendor/mcp/`
- `fetch` is now repo-local too: the shared config points at `tools/mcp/fetch.sh`, which runs a pinned `mcp-server-fetch` environment prepared under `vendor/mcp/fetch`
- The Serena chain is now fully repo-local too: `serena-manager` launches `tools/mcp/serena-agent.sh`, which runs the vendored `vendor/mcp/serena-agent/pylib/serena` package instead of `/home/admin101/.local/bin/uvx`
- `serena-manager` has no external pull/update step anymore; update its source directly in `vendor/mcp/serena-manager`
- `mcp-update-all` updates the externally versioned vendored MCPs, including `fetch`, and reports `serena-manager` as repo-local/manual
- `codegraph` is pinned to an exact npm version in `vendor/mcp/codegraph/package.json`; version bumps should happen through the update command or script so the lockfile stays in sync
- Runtime wrappers under `tools/mcp/` no longer self-heal with host `uv` / `npm` / `node`; they read repo-local toolchain paths from `vendor/toolchain/runtime-env.sh` and fail fast if preflight has not prepared the repo-local runtime
- `mcp-preflight` downloads the pinned repo-local toolchain from `toolchain.lock.json`, prepares managed Python/Node paths under `vendor/toolchain/`, and rebuilds stale vendored MCP runtimes before any CLI launches them
- If a repo-local MCP runtime is missing or cannot bootstrap, sync fails fast instead of falling back to a user-home installation
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
