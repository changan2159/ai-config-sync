# Serena Tool Map

Use this file when the generic Serena workflow triggers and you need a quick mapping from task shape to tool choice.

## Project Setup

- Activate a workspace: `activate_project`
- Confirm Serena readiness: `check_onboarding_performed`
- Create first-time project memory/indexing state: `onboarding`
- Inspect current Serena config and active project: `get_current_config`

## Dynamic Memory

- Discover relevant memory names: `list_memories`
- Read current task context: `read_memory`
- Persist low-risk learned context: `write_memory`
- Refine or correct a memory: `edit_memory`
- Remove a memory only when explicitly intended: `delete_memory`

## Structure Discovery

- File-level structure snapshot: `get_symbols_overview`
- Precise symbol lookup: `find_symbol`
- Reference and call-flow tracing: `find_referencing_symbols`
- Non-symbol-friendly config/docs/string search: `search_for_pattern`

## Symbol-Oriented Edits

Use these only after the target symbol and scope are verified:

- Replace a method/class body: `replace_symbol_body`
- Insert a new symbol before another: `insert_before_symbol`
- Insert a new symbol after another: `insert_after_symbol`
- Rename with impact propagation: `rename_symbol`
- Delete only when unused: `safe_delete_symbol`

## Fallback Rule

If Serena is unavailable, or the files are outside the active Serena project, fall back to shell/file inspection and state that Serena could not anchor the task.
