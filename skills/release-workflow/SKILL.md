---
name: release-workflow
description: Use when preparing releases, changelogs, release notes, version bumps, semantic version decisions, tags, GitHub releases, package publishing, pre-release checklists, or summarizing merged work for users. Prefer this skill when the task crosses commits, PRs, tags, package metadata, CI state, or public-facing release communication.
---

# Release Workflow

Use this skill to prepare releases from evidence in the repository and GitHub state. Keep versioning, changelog text, and release risk tied to actual changes.

## Workflow

1. Identify release target: app, package, plugin, skill, docs, or internal milestone.
2. Inspect current version sources: package manifests, project files, changelog, tags, and release branches.
3. Gather changes from commits, PRs, or diff range.
4. Classify changes: breaking, feature, fix, security, performance, docs, maintenance.
5. Choose version bump using project convention or semantic versioning when applicable.
6. Draft release notes with user-facing impact first and technical detail second.
7. Verify required checks: tests, build, packaging, changelog, tag, publish dry run, or CI status.

## Safety Rules

- Do not create tags, publish packages, or push releases unless the user explicitly asks.
- Do not invent changelog entries that are not supported by commits, PRs, or diffs.
- Preserve the repository's existing changelog format.
- If release state depends on GitHub, use `gh` when available and summarize the checked source.
- Use `dependency-upgrade` when the release is mainly a dependency or framework upgrade.

## Output Expectations

- State the release range or source of changes.
- Provide version bump rationale.
- Provide release notes in the repo's format.
- State verification status and any blockers before publish/tag.
