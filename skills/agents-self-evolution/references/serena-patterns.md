# Serena-First Patterns

Use Serena as the first choice for dynamic project memory and structure discovery when an active project is available.
When the task is explicitly about Serena itself or needs a language-agnostic Serena-first entrypoint, use `serena-workflow`.

## Activation Flow

1. Activate the project.
2. Check whether onboarding has been performed.
3. Read relevant Serena memories if they already exist.
4. Use Serena symbol/search tools to confirm code structure.
5. Write low-risk dynamic learnings to Serena memories.
6. Promote only shared, durable knowledge into repo files.

## Suggested Memory Names

- `ai/corrections`
- `ai/observations`
- `ai/learned-rules`
- `ai/evolution-log`
- `ai/open-questions`

## What Stays In Serena

- Temporary corrections.
- Candidate rules not yet promoted.
- Exploration notes.
- Conflicts and unresolved questions.
- Per-project conventions discovered during ongoing work.

## What Moves To Repo Files

- Business rules that should be reviewed and shared.
- Glossary terms relied on by the whole team.
- Workflow definitions.
- Project structure maps.
- Architecture decisions.
- Stable verification commands and entry points.

## Structure Discovery

Prefer these Serena tools:

- `get_symbols_overview` for file-level structure.
- `find_symbol` for precise code ownership.
- `find_referencing_symbols` for dependency and call flow.
- `search_for_pattern` when structure is not symbol-friendly or spans config/docs.

Use raw shell search only when Serena is unavailable or the files are outside the active project.

## Promotion Rule

Promote a Serena memory into repo docs or `AGENTS.md` only when:

- It is verified.
- It is stable.
- Future collaborators or agents need it.
- It benefits from code review or versioning.

If those are not true, keep it in Serena.
