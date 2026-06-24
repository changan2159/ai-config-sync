---
name: csharp-symbolic-workflow
description: Use when working in C# or .NET codebases and the task involves changing code, debugging, reviewing, refactoring, tracing dependencies, or understanding where behavior is registered or called. Prefer this skill for solution-based repositories with .sln or .csproj files, especially when DI, interfaces, ASP.NET Core, Autofac, MediatR, modular registration, or EF Core schema changes make plain text search insufficient.
---

# C# Symbolic Workflow

Use symbol-aware tooling first when it is available. In Codex, prefer `serena` or another symbol-aware MCP server for `definition`, `references`, `implementations`, `call hierarchy`, symbol search, and rename impact analysis.

Text search still matters, but it is secondary. Use text search to find config keys, route fragments, SQL, log messages, feature flags, option names, and other string-driven behavior that symbol tooling cannot see well.

Default expectation: for brownfield .NET analysis, review, debugging, or refactor work, start by anchoring the repository in Serena. Activate the project and check onboarding before relying on raw `rg` or broad full-file reads. Fall back only when Serena is unavailable or the relevant files lie outside the active project.

## Workflow

1. Anchor the repo in Serena.
- Activate the target project.
- Check onboarding state.
- Read only the memories that are likely to matter for the task.
- If Serena cannot anchor the task, say so plainly and continue with raw search.

2. Confirm the repo shape.
- Look for `.sln`, `.csproj`, `Directory.Build.props`, `Directory.Packages.props`, `Program.cs`, DI registration extensions, module registration, and test projects.
- If the codebase is solution-based or split across projects, assume symbolic navigation is necessary.
- If the task involves integration or smoke tests, inspect test bootstrap code as part of the repo shape, not as disposable scaffolding.

3. Start from symbols, not guesses.
- Find the target type or method definition.
- Inspect references and implementations before editing.
- Use call hierarchy for entrypoints, interface dispatch, handlers, controllers, services, repositories, and event flows.
- When multiple implementations exist, identify the one actually wired into DI or runtime registration.

4. Use text search to fill the gaps.
- Search for strings related to configuration, route templates, audit logs, SQL, background job names, HTTP client names, options section names, and reflection-based registration.
- In ASP.NET Core and Autofac codebases, expect some behavior to be hidden behind extension methods, module scanning, or loaded assemblies.

5. Read the real path end to end.
- For a requested change, read the controller or API entrypoint, service or handler, domain logic, persistence edge, and the registration path that makes the code reachable.
- Do not rely on one search hit or one symbol result when the behavior crosses projects.

For large or risky work, summarize this as a compact brownfield map before planning edits. If sequencing or multi-session execution matters, route through `project-orchestration`.

6. Edit narrowly and verify.
- Make the smallest coherent change.
- Prefer focused verification with `dotnet build`, `dotnet test`, or a target project build over broad unverified edits.
- If rename or signature changes are involved, review the full symbol impact before finalizing.

If multiple independent slices are safe to change in parallel, define explicit ownership first and use `parallel-execution` rather than informal parallelism.

## Heuristics

- Prefer symbol tools first for:
- Interfaces and implementations
- Dependency injection registration
- ASP.NET Core request flow
- MediatR handlers and pipeline behaviors
- Cross-project refactors
- Code review impact analysis
- Rename operations

- Prefer text search first for:
- Error messages
- Log templates
- Route fragments
- Config keys
- SQL
- JSON fields
- Comments or docs that name a feature without matching type names

- Treat symbol results as high-quality navigation, not absolute truth.
- Be extra careful with reflection, assembly scanning, attributes, source generators, dynamic registration, and string-based dispatch. In those cases, combine symbol navigation with text search and runtime/build validation.

## .NET-Specific Checks

- Inspect `Program.cs` or startup composition first.
- For integration tests, also inspect `WebApplicationFactory`, `TestServer`, repository locators, fixture bootstrapping, and configuration overrides.
- Inspect service registration extensions and container modules.
- Check whether controllers are discovered by assembly scan rather than direct reference.
- Check whether modules expose hooks or registrars that are wired indirectly.
- Check `appsettings*.json`, options classes, and `IOptions<T>` bindings when behavior depends on configuration.
- EF Core schema-change checklist:
  - If the edit changes entities, configurations, indexes, defaults, nullability, or constraints, stop and check the latest migration chain before finalizing.
  - Generate the matching migration and its `.Designer.cs`.
  - Verify model/migration drift with `dotnet ef migrations has-pending-model-changes` or the repo's equivalent command.
  - If runtime failures mention missing tables, columns, or constraints, treat schema drift or an unapplied migration as a first-class hypothesis before changing query logic.
  - If the target database is already deployed, confirm the migration exists, is applied, and matches the model change that introduced the failure.
  - When live PostgreSQL or SQL Server inspection is needed, use `database-workflow` so schema lookup and readback checks go through the local wrappers.
- If the repository uses analyzers or CI guard scripts, run them when relevant.
- If tests depend on default solution names, seeded accounts, or environment variables, verify those assumptions before changing production code.

## Output Expectations

- Explain the actual execution path you used to choose the edit.
- Mention when a result depends on inference rather than a direct symbol or source hit.
- Cite the specific files you changed or relied on.
- If verification was not run, say so plainly.

If the work is large enough to pause and resume later, leave a compact handoff with the traced execution path, the modules already verified, and the next unresolved dependency or edit point.
