# Agent Integration Notes

This repository is the source of truth for cross-client prompt overlays, shared skills, and managed MCP distribution. Use this file for client-specific invocation details that should not stay hidden in user-home dotfiles.

## Skill Invocation

### Codex

- Shared skills are synced from `skills/shared/` as repository-managed skill directories.
- Codex-only repo skills live under `skills/codex/` and are added through Codex target `skillRoots`.
- Prefer the shared routing defaults in `prompts/shared-global-prompt.md` and the client-specific additions in `prompts/codex-global-prompt.md`.
- When a narrower Codex-only capability is needed, follow the prompt overlay and native Codex tool surface for that session.
- Shared Paseo orchestration skills: `paseo`, `paseo-handoff`, `paseo-advisor`, `paseo-loop`, `paseo-committee`.
- Codex-only repo skill: `codex-subagent`

### Claude Code

- Shared skills are synced into `~/.claude/skills`.
- Claude Code exposes commands and skills from the `/` command menu.
- Direct skill invocation uses `/<name>` after discovery from `/`.
- Shared Paseo orchestration skills are available through the same `/` skill surface once synced.
- Do not invent OpenCode-style `skill-<name>` aliases in Claude sessions.

### OpenCode

- Shared skills are rendered into the OpenCode config as `agent` entries.
- This repository manages the canonical invocation prefix through `targets.opencode.agentPrefix`.
- Current canonical form is `skill-<name>`.
- Shared Paseo orchestration skills therefore invoke as `skill-paseo`, `skill-paseo-handoff`, `skill-paseo-advisor`, `skill-paseo-loop`, and `skill-paseo-committee`.
- OpenCode currently relies on the shared skill set by default; `skills/opencode/` is an intentional placeholder for future OpenCode-only skills rather than a required active skill root today.

### Pi

- Shared skills are synced into `~/.pi/agent/skills-shared`.
- Pi-only repo skills live under `skills/pi/` and are added through the Pi target `skillRoots`.
- Direct skill invocation uses `/skill:<name>`.
- Shared Paseo orchestration skills therefore invoke as `/skill:paseo`, `/skill:paseo-handoff`, `/skill:paseo-advisor`, `/skill:paseo-loop`, and `/skill:paseo-committee`.
- This repository manages `enableSkillCommands` in Pi settings so direct skill commands remain available after sync.
- Shared `fetch`, `serena`, `codegraph`, and `node_repl` MCP servers are configured for direct-tool exposure in Pi, and the managed Pi MCP settings hide the generic `mcp` proxy tool once the direct-tool cache is ready.
- This repository also manages Pi-native capability packages: `pi-goal`, `pi-context-prune`, `pi-context-usage`, `pi-cache-graph`, and `pi-fallback-provider`, in addition to the existing Pi integration packages.
- Pi fallback routing is configured through `~/.pi/fallback-chains.json`; the current managed default is `fallback/default -> openai/gpt-5.4`, and sync treats the chain file as a fully managed payload, rewriting it before switching the Pi default provider.
- Pi context pruning is configured through `~/.pi/agent/context-prune/settings.json`, which sync also treats as a fully managed payload rather than merging with stale keys.
- If Pi prompt, settings, or skills were just synced, restart `pi` or run `/reload` before relying on the updated command set.

## Delegation Mapping

- Shared routing and planning skills should talk about platform-specific delegation, not hard-code one client unless the skill itself is intentionally client-specific.
- Shared Paseo skills are the preferred cross-client orchestration layer when `paseo` is available and provider-backed multi-agent work is actually warranted.
- Codex-only delegation skill: `codex-subagent`
- Pi native delegation package: `pi-subagents`
- Claude Code and OpenCode should use their native subagent or delegation surfaces when one is available for the current session.
- Prefer `codex-subagent` for Codex-local child work when provider contrast is not needed and the work stays inside the current Codex session model.
- Prefer `paseo-handoff`, `paseo-advisor`, `paseo-loop`, or `paseo-committee` when cross-provider contrast, background orchestration, worktree isolation, or multi-client consistency materially helps.

## Routing Notes

- Use `design-review` for visual polish, layout quality, spacing, hierarchy, and presentation review of an existing UI.
- Use `frontend-design-review` for PR review, design-system compliance, component-level review, accessibility review, or implementation review against an existing design spec.
- Use `frontend-design` for creating or redesigning interfaces, and pair it with `frontend-ui-engineering` when component logic, state, or shared interaction patterns are substantial.
- Use `performance` for focused loading, runtime, and resource optimization work.
- Use `core-web-vitals` when the task is specifically about LCP, INP, CLS, or layout-shift diagnosis.
- Use `web-quality-audit` when the request is a broad web audit across performance, accessibility, SEO, and best practices.
- For .NET work, combine `csharp-symbolic-workflow` with `aspnet-core` when both framework guidance and symbol-level brownfield tracing matter; add `aspnet-modular-autofac` when Autofac modules, assembly scanning, or indirect runtime registration are part of the problem.

## Second-Pass Review Defaults

- Shared default: prefer the `code-review` skill for non-trivial second-pass review.
- When provider contrast or independent orchestration would materially reduce risk, escalate to `paseo-advisor` or a read-only `paseo-handoff` review pass after the normal review path.
- Codex: prefer the child verifier agent as the first-pass independent reviewer; if unavailable, invoke the `code-review` skill through the Codex skill surface or reuse the verified non-interactive CLI review commands recorded in `prompts/codex-global-prompt.md`.
- OpenCode: default explicit form is `skill-code-review`.
- Claude Code: use the native `/` skill menu and invoke the shared `code-review` skill there when a second pass is needed.
- Pi: use `/skill:code-review` when direct invocation is needed and the session has reloaded managed settings.

## Managed Sources

- Shared routing and verification policy: `prompts/shared-global-prompt.md`
- Shared sync classification: `docs/shared/sync-scope.md`
- Shared runtime notes: `docs/shared/runtime/linux-serena-dotnet-host-notes.md`
- Shared workflow notes: `docs/shared/workflows/dotnet-workflow-defaults.md`
- Future client-specific repo docs should live under `docs/<client>/`
- Codex overlay: `prompts/codex-global-prompt.md`
- Claude overlay: `prompts/claude-global-prompt.md`
- OpenCode overlay: `prompts/opencode-global-prompt.md`
- Pi overlay: `prompts/pi-global-prompt.md`

## Verification Basis

- Claude Code `/` command and skill invocation behavior: Anthropic Claude Code docs
  - https://docs.anthropic.com/en/docs/claude-code/interactive-mode
  - https://docs.anthropic.com/en/docs/claude-code/skills
- Pi skill command and `enableSkillCommands` behavior: Pi coding agent docs
  - https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md
  - https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md
