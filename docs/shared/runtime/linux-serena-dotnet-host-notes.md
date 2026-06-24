# Linux Serena And .NET Host Notes

This file records Linux host workflow details for sessions on the current Ubuntu host that uses this `ai-config-sync` checkout. Keep prompt references pointed here instead of to user-home dotfiles so host notes stay versioned with the project.

Keep constitutional collaboration defaults in the synced client prompt files; keep host repair steps and path-level environment rules here.

## Serena Startup And Recovery

- Start Serena through the repository-managed MCP chain, not a bare `serena` command.
- If Serena disappears or its runtime drifts, run `mcp-preflight` from the repo root to rebuild the repo-local Serena runtime; do not invent a user-home fallback:
  ```bash
  cd /home/admin101/projects/2026/ai-config-sync
  .venv/bin/python -m ai_config_sync.cli mcp-preflight
  ```
- After `mcp-preflight` succeeds, restart the affected client or MCP session so it picks up the repaired toolchain.
- If `mcp-preflight` itself fails, check `vendor/toolchain/runtime-env.sh` and `toolchain.lock.json` for stale pins; do not fall back to host `uv`, `npm`, or `node` directly.

## .NET Runtime Policy

- Serena's C# Roslyn language server should use the system `.NET` installation on this Ubuntu host: `/usr/bin/dotnet` and `/usr/lib/dotnet` are the default SDK and runtime roots.
- Do not reintroduce a user-level SDK or runtime install under `~/.dotnet` into the default `PATH` or extension SDK resolution chain.
- A minimal `~/.dotnet` metadata or cache directory may be recreated by first-run tooling. That is acceptable as long as it does not contain the active SDK or runtime root and is not added back to `PATH`.
- `/usr/lib/dotnet` must remain package-managed and internally consistent. Do not manually overlay extracted SDK or runtime tarballs there or mix ad hoc SDK bands with distro-managed host files.
- If another SDK band is needed, install it through the system package manager or change the repository `global.json` to an installed version instead of mutating the shared runtime root by hand.

## Related Managed Guidance

- Cross-project `.NET` CLI tool and EF Core workflow defaults live in `docs/shared/workflows/dotnet-workflow-defaults.md`.
