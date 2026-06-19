---
name: dependency-upgrade
description: Use when upgrading packages, frameworks, SDKs, lockfiles, test frameworks, build tools, npm/pnpm/yarn dependencies, NuGet packages, .NET SDK or target frameworks, browser tooling, React/Next/Vite/Tailwind, or resolving dependency conflicts and security-vulnerable dependencies. Prefer this skill when version changes may introduce breaking changes, peer dependency drift, migration steps, lockfile churn, or staged verification needs.
---

# Dependency Upgrade

Use this skill to make dependency changes deliberately: understand current versions, upgrade in safe stages, read migration notes, and verify behavior after each meaningful step.

## Workflow

1. Identify package manager and lockfiles.
2. Record current versions and why the upgrade is needed: security, compatibility, feature, or maintenance.
3. Read authoritative release notes or migration guides for major version changes.
4. Upgrade in the smallest coherent stage: runtime packages, build tools, test tools, or framework versions.
5. Run install/restore and inspect peer/dependency warnings.
6. Run focused verification, then broader build/test checks if the blast radius is large.
7. Summarize changed packages, migration edits, and remaining risks.

## Ecosystem Checks

- Node: inspect `package.json`, lockfile, package manager, engines, peer dependency warnings, and scripts.
- .NET: inspect `.sln`, `.csproj`, `global.json`, `Directory.Packages.props`, target frameworks, analyzers, and NuGet lock mode if used.
- Frontend frameworks: check framework-specific migration guides and generated config changes.
- Test frameworks: check assertion APIs, fixture lifecycle, browser binaries, snapshots, and reporters.

## Safety Rules

- Do not update every package just because a tool can.
- Avoid mixing unrelated major upgrades in one step.
- Preserve lockfile consistency with the repo's package manager.
- Treat generated lockfile churn as meaningful; inspect it.
- If a security fix requires a major upgrade, state the compatibility risk explicitly.
- For large migrations, combine with `large-refactor` or `project-orchestration`.

## Output Expectations

- State old and new versions for important packages.
- Cite the migration source or release note when it drove a code change.
- List commands run and whether install, build, lint, and tests passed.
- Call out any skipped checks or unresolved peer warnings.
