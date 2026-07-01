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
/home/admin101/projects/2026/ai-config-sync/prompts/shared-global-prompt.md
```

Codex-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/prompts/codex-global-prompt.md
```

Claude-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/prompts/claude-global-prompt.md
```

OpenCode-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/prompts/opencode-global-prompt.md
```

Pi-specific global prompt overlay:

```text
/home/admin101/projects/2026/ai-config-sync/prompts/pi-global-prompt.md
```

Shared skill sources:

```text
/home/admin101/projects/2026/ai-config-sync/skills/shared
```

Client-specific skill sources:

```text
/home/admin101/projects/2026/ai-config-sync/skills/codex
```

Repo-managed agent integration notes:

```text
/home/admin101/projects/2026/ai-config-sync/docs/shared/agent-integration.md
```

Shared sync scope audit (what is shared vs target-specific):

```text
/home/admin101/projects/2026/ai-config-sync/docs/shared/sync-scope.md
```

Repo-managed shared host and `.NET` workflow notes:

```text
/home/admin101/projects/2026/ai-config-sync/docs/shared/runtime/linux-serena-dotnet-host-notes.md
/home/admin101/projects/2026/ai-config-sync/docs/shared/workflows/dotnet-workflow-defaults.md
```

Repo-local MCP wrappers:

```text
/home/admin101/projects/2026/ai-config-sync/tools/mcp
```

Client-specific MCP wrappers should live under:

```text
/home/admin101/projects/2026/ai-config-sync/tools/mcp/<client>
```

Shared MCP wrappers live under:

```text
/home/admin101/projects/2026/ai-config-sync/tools/mcp/shared
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
.venv/bin/python -m ai_config_sync.cli mcp-add fetch --server-command "${PWD}/tools/mcp/shared/fetch.sh"
.venv/bin/python -m ai_config_sync.cli mcp-remove fetch
```

Bootstrap Pi in a fresh environment; this installs Pi itself, prepares repo-local MCP runtimes, and syncs managed Pi plugins/config in one pass:

```bash
.venv/bin/python -m ai_config_sync.cli pi-bootstrap
pi --version
```

Install or update only the Pi CLI runtime:

```bash
.venv/bin/python -m ai_config_sync.cli pi-install
.venv/bin/python -m ai_config_sync.cli pi-install --version 0.73.0
.venv/bin/python -m ai_config_sync.cli pi-status
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

Install or start `pi-web` for browser-based Pi sessions:

```bash
.venv/bin/python -m ai_config_sync.cli pi-web-install
.venv/bin/python -m ai_config_sync.cli pi-web-install --version 1.21.2
sudo .venv/bin/python -m ai_config_sync.cli pi-web-service-install
sudo .venv/bin/python -m ai_config_sync.cli pi-web-service-start
.venv/bin/python -m ai_config_sync.cli pi-web-status
```

Update an existing managed install:

```bash
.venv/bin/python -m ai_config_sync.cli opencode-install --version 1.17.8
sudo systemctl restart opencode-web.service
```

Script entrypoints:

```bash
./scripts/paseo/update-paseo.sh
./scripts/paseo/update-paseo.sh 0.1.101
./scripts/codex/update-codex.sh
./scripts/codex/update-codex.sh 0.142.0
./scripts/claude/update-claude.sh
./scripts/claude/update-claude.sh 2.1.183
./scripts/opencode/update-opencode.sh
./scripts/opencode/update-opencode.sh 1.17.8
./scripts/pi/update-pi.sh
./scripts/pi/update-pi.sh 0.73.0
./scripts/pi-web/update-pi-web.sh
./scripts/pi-web/update-pi-web.sh 1.21.2
./update-all-clients.sh
./update-all-clients.sh --with-pi-web
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
- Claude is managed under the user prefix `/home/admin101/.local`; `scripts/claude/update-claude.sh` installs `@anthropic-ai/claude-code` into that prefix directly because the native self-updater proved unreliable on this host
- `scripts/paseo/update-paseo.sh` reuses the current Paseo npm install prefix, updates `@getpaseo/cli`, backs up `~/.paseo/config.json` when present, and restarts the local daemon from `PASEO_HOME` or `~/.paseo` while reusing the current listen/relay mode when status data is available
- `scripts/codex/update-codex.sh` reuses the current Codex npm install prefix and escalates through `sudo` automatically when the existing global prefix is not user-writable
- `scripts/claude/update-claude.sh` also pins VS Code's `claudeCode.claudeProcessWrapper` setting to `/home/admin101/.local/bin/claude` so the extension can launch Claude even when the editor process does not inherit `~/.local/bin` on `PATH`
- `update-all-clients.sh` runs the managed Paseo, Codex, Claude, OpenCode, and Pi update scripts in sequence; add `--with-pi-web` to include the Pi web service runtime too
- Plugin cache skills are not synced by default
- Shared skill sync mirrors direct child skills under repo-local `skills/shared/`; for Codex these managed links are written into `~/.codex/skills` so the current Codex Desktop discovery path can expose them in new threads, while client-specific repo skills live under `skills/<client>/` and are attached only from that target's `skillRoots`
- OpenCode skills are rendered as `agent` entries from the same `SKILL.md` sources; OpenCode has no file-system `skillsDir` — skills are distributed as config entries rather than synced directories, so the `opencode` target intentionally omits `skillsDir`
- Pi skills are symlinked into `/home/admin101/.pi/agent/skills-shared`, Pi-only repo skills are sourced from `skills/pi/`, `~/.pi/agent/settings.json` keeps those directories plus the managed Pi packages (`npm:pi-mcp-adapter`, `npm:@narumitw/pi-plan-mode`, `npm:pi-subagents`, `npm:pi-goal`, `npm:pi-context-prune`, `npm:pi-context-usage`, `npm:pi-cache-graph`, `npm:pi-fallback-provider`) registered, sync also installs or removes those packages under `/home/admin101/.pi/agent/npm`, sync manages `enableSkillCommands: true` so `/skill:<name>` stays available, shared `fetch`/`serena`/`codegraph`/`node_repl` MCP servers are exposed to Pi as direct tools, and Pi model defaults/providers can be synced into `~/.pi/agent/settings.json`, `~/.pi/agent/models.json`, `~/.pi/fallback-chains.json`, and `~/.pi/agent/context-prune/settings.json`
- Pi defaults are configured to start on `fallback/default`, and sync now writes fallback runtime files before switching the default provider so startup does not see a half-applied fallback state
- Shared MCP servers belong in top-level `mcpServers` and should point at `tools/mcp/shared/`; client-specific repo MCP wrappers should live under `tools/mcp/<client>/` and be declared in that target's `mcpServers`
- Managed OpenCode runtime installs live under `/home/admin101/.local/share/ai-config-sync/opencode/releases/<version>` as official release binaries instead of `/usr/local/lib/node_modules`
- `/home/admin101/.local/bin/opencode` is a managed wrapper that probes `current` first and falls back to the previous healthy release if the current one is broken
- `opencode-install` resolves the latest version from the official GitHub releases API, downloads the matching release asset for the current host, validates both `opencode --version` and a short-lived `opencode serve` probe, and only then switches the `current` symlink
- The canonical boot path is the system service `/etc/systemd/system/opencode-web.service`, which runs as the login user but starts from `multi-user.target` instead of depending on a user-session service
- `opencode-service-start` disables the old user unit `opencode-web-managed.service` before enabling the system service, so future updates do not recreate the previous port-conflict path
- `pi-web-install` uses the official upstream installer, keeps the binary under `/home/admin101/.local/bin/pi-web`, and preserves upstream default plugin installation unless the environment overrides it
- The canonical Pi web boot path is the system service `/etc/systemd/system/pi-web.service`, which runs `pi-web --port 8732 --host 0.0.0.0` as the login user
- `loginctl linger` may still remain enabled on this host for `ai-config-sync.service`, but OpenCode itself no longer depends on a user service or linger to start after boot
- MCP commands point at repo-local wrapper scripts under `tools/mcp/shared/` or `tools/mcp/<client>/`, and those wrappers bootstrap only the vendored repo-local runtimes under `vendor/mcp/`
- `fetch` is now repo-local too: the shared config points at `tools/mcp/shared/fetch.sh`, which runs a pinned `mcp-server-fetch` environment prepared under `vendor/mcp/fetch`
- The Serena chain is now fully repo-local too: `serena-manager` launches `tools/mcp/shared/serena-agent.sh`, which runs the vendored `vendor/mcp/serena-agent/pylib/serena` package instead of `/home/admin101/.local/bin/uvx`
- `serena-manager` has no external pull/update step anymore; update its source directly in `vendor/mcp/serena-manager`
- `mcp-update-all` updates the externally versioned vendored MCPs, including `fetch`, and reports `serena-manager` as repo-local/manual
- `codegraph` is pinned to an exact npm version in `vendor/mcp/codegraph/package.json`; version bumps should happen through the update command or script so the lockfile stays in sync
- Runtime wrappers under `tools/mcp/shared/` and `tools/mcp/<client>/` no longer self-heal with host `uv` / `npm` / `node`; they read repo-local toolchain paths from `vendor/toolchain/runtime-env.sh` and fail fast if preflight has not prepared the repo-local runtime
- `mcp-preflight` downloads the pinned repo-local toolchain from `toolchain.lock.json`, prepares managed Python/Node paths under `vendor/toolchain/`, and rebuilds stale vendored MCP runtimes before any CLI launches them
- `sync-once` and watch-mode resyncs now run `mcp-preflight` before writing managed outputs, so Serena and the other repo-local MCP runtimes get refreshed automatically when their managed source inputs drift
- If a repo-local MCP runtime is missing or cannot bootstrap, sync fails fast instead of falling back to a user-home installation
- Codex sync currently supports only `stdio` MCP servers; remote MCP entries in the shared source will fail fast when a Codex target is enabled
- OpenCode keeps unrelated JSONC content and comments, but the managed `mcp` and `agent` sections are rewritten on sync
- `stdio` MCP entries must define `command`; sync now fails fast instead of writing broken Codex, Claude, or OpenCode config
- Symlinked config and prompt targets are updated in-place at their real destination instead of being replaced with regular files
- Skill sync keeps a local manifest in each managed skills directory so state-file loss can still clean up stale shared links without deleting unrelated manual symlinks
- Watch mode logs sync errors and keeps running instead of exiting on the first transient failure

## Global Prompt Config

`shared-ai-config.json` supports:

- top-level `include`: skill allowlist applied across the configured skill roots; `["*"]` means every discovered skill, while target-specific skill names are included only on targets that actually expose them
- top-level `globalPromptPath`: the shared source file to copy, typically `prompts/shared-global-prompt.md`
- top-level `skillRoots`: shared skill roots synced to every managed target, typically `skills/shared`
- per-target `skillRoots`: target-only skill roots such as `skills/codex`
- top-level `mcpServers`: shared MCP servers synced to every managed target, typically backed by `tools/mcp/shared`; Pi also honors adapter-specific fields such as `directTools` and `toolTimeoutSec` when writing the standard MCP config
- Pi target `mcpSettings`: optional managed top-level Pi MCP adapter settings such as `disableProxyTool`
- per-target `mcpServers`: target-only MCP servers, typically backed by wrappers under `tools/mcp/<client>/`
- per-target `globalPromptPath`: the destination file for that client
- per-target `globalPromptAppendPath`: optional client-specific content appended after the shared core with a blank line separator, typically under `prompts/`
- Pi target `defaultProvider` / `defaultModel`: optional default model selection written into `settings.json`; this repo currently uses `fallback/default`
- Pi target `enableSkillCommands`: optional managed toggle written into `settings.json`
- Pi target `modelsPath`: optional `models.json` destination; defaults to a sibling `models.json` next to `settings.json`
- Pi target `providers`: optional managed `models.json` provider definitions merged by provider name without deleting unrelated manual providers
- Pi target `fallbackChainsPath` / `fallbackChains`: optional fallback provider chain file and managed chains written by name
- Pi target `contextPruneSettingsPath` / `contextPruneSettings`: optional `pi-context-prune` settings file and managed key/value payload

If a target has no prompt destination, prompt sync is skipped for that target while MCP and skill sync continue.
If the shared core is omitted but a target defines both `globalPromptPath` and `globalPromptAppendPath`, the target prompt is generated from that overlay alone.

## Recovery Notes

- Sync state lives at `state/sync-state.json`
- Managed skill directories also store `.ai-config-sync-managed.json`; if `state/sync-state.json` is lost, the next sync still knows which shared skill links it owns
- Prompt files from a previous sync are removed automatically when that target prompt is disabled or moved
- Atomic writes are used for synced prompts, target configs, the state file, the skill manifest, and the generated service file so an interrupted sync is less likely to leave partial output behind
