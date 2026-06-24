# .NET Workflow Defaults

This file records cross-project `.NET` and EF Core workflow defaults managed by this repository. Keep machine-specific runtime and Serena host details in `docs/shared/runtime/linux-serena-dotnet-host-notes.md`.

## CLI Tool Defaults

- Prefer per-repository local `.NET` CLI tool manifests such as `.config/dotnet-tools.json`.
- Do not rely on `dotnet tool install --global` or `~/.dotnet/tools` as the default workflow.
- Only use a machine-level shared tool path such as `/usr/local/share/dotnet-tools` with an explicit user request or a documented machine-wide operations reason.

## EF Core Migration Defaults

- EF Core migrations are mandatory tool-generated artifacts. Use `dotnet ef migrations add`.
- Do not handwrite or manually patch migration classes, model snapshots, or migration metadata as a substitute for the tool-generated workflow.
- Before running any `dotnet ef` command, ensure the solution has been restored:
  1. `dotnet restore` — restore NuGet packages for all projects in the solution.
  2. `dotnet tool restore` — restore repo-local tools from `.config/dotnet-tools.json`.
  3. Then run the EF Core command.
- When EF Core schema work is needed and `dotnet-ef` is unavailable, provision the repo-local tool workflow first: ensure `.config/dotnet-tools.json` exists, add `dotnet-ef` when missing, run `dotnet tool restore`, and then generate the migration with the tool.
- In multi-project solutions, use `--project` and `--startup-project` to avoid ambiguous project resolution:
  ```bash
  dotnet ef migrations add <MigrationName> \
    --project src/MyApp.Infrastructure \
    --startup-project src/MyApp.Api
  ```
  Use `--project` for the project that contains the `DbContext` and migrations, and `--startup-project` for the runnable entry point that provides the `IDesignTimeDbContextFactory` or DI configuration.
- If repo-local `dotnet-ef` restore or install fails, treat that as a tooling defect to diagnose and fix before continuing. Do not bypass the failure by hand-authoring EF migrations or snapshot changes.
