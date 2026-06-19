---
name: serena-workflow
description: Use when the task is primarily about Serena project activation, onboarding, memory reads or writes, symbol-aware structure discovery, or Serena-first brownfield navigation independent of any one programming language. Prefer this skill when Serena should be the default operating surface before falling back to raw text search.
---

# Serena Workflow

Use this skill when Serena itself is the workflow anchor.

This is the generic Serena-first skill for:

- activating a project
- checking onboarding state
- reading and writing Serena memories
- exploring a codebase with symbol-aware tools
- verifying structure before edits, plans, or documentation

If the task is language-specific and a narrower Serena-based skill exists, combine with that skill instead of replacing it. For example, use `csharp-symbolic-workflow` for .NET-specific tracing and `agents-self-evolution` for end-of-task persistence.

## Default Flow

1. Activate the target project.
2. Check whether onboarding has already been performed.
3. Read only the Serena memories that are likely to matter for the current task.
4. Use Serena symbol/search tools to confirm the relevant structure before making assumptions.
5. Execute the task with the smallest coherent edit, plan, or analysis.
6. Write only low-risk dynamic learnings back to Serena memories.
7. Promote only shared, durable, evidence-backed knowledge into repo docs or `AGENTS.md`.

If Serena is unavailable for the current workspace, say so plainly and fall back to raw shell search or local file inspection.

## Tool Selection

Prefer these Serena tools first:

- `activate_project`
- `check_onboarding_performed`
- `onboarding`
- `list_memories`
- `read_memory`
- `write_memory`
- `edit_memory`
- `get_symbols_overview`
- `find_symbol`
- `find_referencing_symbols`
- `search_for_pattern`

Use edit-oriented Serena tools only when you already understand the target symbol and the write scope is clear:

- `replace_symbol_body`
- `insert_before_symbol`
- `insert_after_symbol`
- `rename_symbol`
- `safe_delete_symbol`

For a quick tool-to-task map, read `references/tool-map.md`.

## Heuristics

- Use symbol-aware Serena navigation before broad text search when the files are inside the active project.
- Use `search_for_pattern` for config keys, SQL, logs, routes, JSON fields, docs, and other string-driven behavior that symbol tools do not capture well.
- Treat Serena memories as dynamic working context, not as a replacement for reviewed repo documentation.
- Do not add `.serena/` to global or project ignore files. Project-level Serena configuration and memories must remain portable with the repository; if cache noise must be ignored, restrict it to a narrow cache-only path after inspecting the project.
- Keep memory writes narrow, evidence-backed, and reversible.
- If the structure is still unclear, stay read-heavy until the execution path is understood.

Task-shape guidance:

- Serena-first is the default for brownfield analysis, cross-file tracing, symbol impact analysis, and dependency or registration discovery.
- Serena is optional for medium-complexity tasks where you know the likely files but still need to confirm one or two symbol relationships.
- Serena is usually unnecessary for pure string search, config-only work, docs-only work, template edits, or tiny localized edits in files already identified by the user.
- If symbol-aware results become noisy or low-value because the code relies heavily on reflection, dynamic dispatch, code generation, or external configuration, combine Serena with raw search instead of forcing an all-Serena workflow.

## When To Combine With Other Skills

- Use `csharp-symbolic-workflow` for .NET-specific symbol tracing and DI/runtime wiring.
- Use `project-orchestration` when the first decision is whether the task needs a quick path or a phased path.
- Use `systematic-debugging` when the failure is non-obvious and root cause is still unknown.
- Use `agents-self-evolution` when discovered context should be persisted beyond dynamic Serena memory.

## Output Expectations

- State whether Serena was available and used.
- Explain which Serena tools anchored the result.
- Distinguish direct source evidence from inference.
- Say when you had to fall back to raw search or non-Serena tooling.
