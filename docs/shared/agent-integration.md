# Agent Integration Notes

This repository is the source of truth for cross-client prompt overlays, shared skills, and managed MCP distribution. Use this file for client-specific invocation details that should not stay hidden in user-home dotfiles.

## Skill Invocation

### Codex

- Shared skills are synced from `skills/shared/` as repository-managed skill directories.
- Codex-only repo skills live under `skills/codex/` and are added through Codex target `skillRoots`.
- Prefer the shared routing defaults in `prompts/shared-global-prompt.md` and the client-specific additions in `prompts/codex-global-prompt.md`.
- When a narrower Codex-only capability is needed, follow the prompt overlay and native Codex tool surface for that session.
- Codex-only repo skill: `codex-subagent`

### Claude Code

- Shared skills are synced into `~/.claude/skills`.
- Claude Code exposes commands and skills from the `/` command menu.
- Direct skill invocation uses `/<name>` after discovery from `/`.
- Do not invent OpenCode-style `skill-<name>` aliases in Claude sessions.

### OpenCode

- Shared skills are rendered into the OpenCode config as `agent` entries.
- This repository manages the canonical invocation prefix through `targets.opencode.agentPrefix`.
- Current canonical form is `skill-<name>`.

### Pi

- Shared skills are synced into `~/.pi/agent/skills-shared`.
- Direct skill invocation uses `/skill:<name>`.
- This repository manages `enableSkillCommands` in Pi settings so direct skill commands remain available after sync.
- If Pi prompt, settings, or skills were just synced, restart `pi` or run `/reload` before relying on the updated command set.

## Delegation Mapping

- Shared routing and planning skills should talk about platform-specific delegation, not hard-code one client unless the skill itself is intentionally client-specific.
- Codex-only delegation skill: `codex-subagent`
- Pi native delegation package: `pi-subagents`
- Claude Code and OpenCode should use their native subagent or delegation surfaces when one is available for the current session.

## Second-Pass Review Defaults

- Shared default: prefer the `code-review` skill for non-trivial second-pass review.
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
