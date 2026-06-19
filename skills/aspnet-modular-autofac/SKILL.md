---
name: aspnet-modular-autofac
description: Use when working in modular ASP.NET Core backends that compose services through Program.cs, extension methods, Autofac modules, assembly scanning, module registrars, or runtime discovery hooks. Prefer this skill when the codebase uses multiple .csproj projects and behavior is wired indirectly through DI or module managers rather than only direct controller-to-service references.
---

# ASP.NET Modular Autofac

This skill is for solution-based ASP.NET Core backends where request flow and service wiring are spread across host startup, DI extensions, Autofac container modules, and module discovery. Use it together with symbol-aware navigation when AI needs to change behavior without missing the real registration path.

## Workflow

1. Start at the host.
- Read `Program.cs` first.
- Identify where services are added to `IServiceCollection`.
- Identify where Autofac replaces or augments built-in DI.
- Identify middleware and endpoint mapping order before changing request behavior.

2. Trace registration, not just implementation.
- Follow `AddXyz(...)`, `ConfigureXyz(...)`, and registrar extension methods.
- Inspect Autofac modules, container builders, and registration extensions before assuming a service is unused or safe to replace.
- If a service has multiple implementations, determine which one is actually registered in the target environment.

3. Look for indirect module composition.
- Check for assembly scanning, loaded-assembly controller discovery, module managers, `IModule*` hooks, registrars, and convention-based endpoint mapping.
- Treat these as part of the execution path, not optional infrastructure.
- If code is discovered by scanning, verify both the contract and the discovery mechanism.

4. Reconstruct the actual runtime path.
- For HTTP behavior, trace: host startup -> middleware -> controller or mapped endpoint -> application service or handler -> domain logic -> persistence or integration.
- For background or module-driven behavior, trace: startup registration -> hosted service or module hook -> invoked service chain.
- Be explicit when part of the path is inferred from conventions rather than direct calls.

5. Verify with the smallest meaningful check.
- Use project-targeted `dotnet build` first when changing registration or signatures.
- Use targeted tests when available.
- If no tests exist, verify the touched startup path or module entrypoint through focused build and manual reasoning.

## What To Inspect First

- `Program.cs`
- Host-level extension methods under `Extensions/`
- Autofac `Module` implementations
- DI registration helpers
- Controller or endpoint discovery helpers
- Module managers, registrars, or web hooks
- Options binding and `appsettings*.json` when behavior depends on config

## Common Failure Modes

- Editing an implementation without changing the registration that actually resolves it
- Changing a controller or endpoint while missing middleware order dependencies
- Missing convention-based module discovery or assembly scanning
- Assuming one project owns a behavior that is actually completed in another project
- Breaking startup by changing a constructor or options type without checking DI bindings
- Renaming symbols without reviewing cross-project references and implementations

## When To Combine With Other Skills

- Use `csharp-symbolic-workflow` for symbol-first navigation and impact analysis.
- Use `aspnet-core` when framework-level guidance or version-correct ASP.NET Core behavior matters.
- Use `systematic-debugging` when the startup path, registration chain, or runtime behavior is unclear.

## Output Expectations

- Explain which startup and registration points make the edited code reachable.
- Distinguish direct source evidence from convention-based inference.
- Mention the concrete verification performed, especially when startup, DI, or middleware ordering changed.
