---
name: python-workflow
description: Use when working in Python applications, libraries, CLIs, scripts, services, or automation where repo conventions, environment management, testing, packaging, or framework patterns matter. Prefer this for FastAPI, Flask, Django, Typer/Click CLIs, pytest-based work, and brownfield Python repositories where ad hoc edits would miss runtime or tooling conventions.
---

# Python Workflow

Use this skill when Python is the main implementation language and the task needs more than generic coding advice.

The goal is to make Python changes in a way that respects the repository's runtime, environment, packaging, test, and framework conventions.

## When To Use

Use this skill when:

- editing Python application code, services, CLIs, scripts, or libraries
- working in FastAPI, Flask, Django, Typer, Click, or pytest-based repositories
- debugging Python test failures, import issues, virtualenv drift, packaging issues, or script behavior
- adding or changing Python automation in a brownfield repo
- you need to decide whether logic belongs in app code, a script, a shared module, or test helpers

Pair with:

- `serena-workflow` when symbol-aware brownfield tracing matters
- `systematic-debugging` when the failure is not yet understood
- `test-driven-development` when behavior-first tests are practical
- `code-maintainability` for non-trivial changes
- `dependency-upgrade` for package or interpreter upgrades

## Default Flow

1. Confirm the Python runtime and environment shape already used by the repo.
2. Reuse the repo's existing entrypoints, test commands, formatters, and package manager.
3. Keep changes in the narrowest owner: app module, CLI command, script helper, or test fixture.
4. Prefer focused verification before broader test runs.
5. Preserve existing packaging and invocation patterns unless the task explicitly changes them.

## Environment And Tooling

Prefer the repository's existing workflow first:

- `python -m ...` or `.venv/bin/python -m ...` when the repo uses a virtualenv
- `pytest` or the repo's test wrapper for tests
- existing `pyproject.toml`, `requirements*.txt`, `poetry.lock`, `uv.lock`, or similar as the packaging source of truth
- existing lint or format commands rather than inventing new ones

Do not silently switch package managers or env managers.
If the repo uses `.venv`, prefer that over host-global Python.
If the environment is unclear, inspect the repo before assuming `poetry`, `uv`, `pip`, or `tox`.

## Coding Rules

- Keep import and module boundaries consistent with the repo's structure.
- Prefer small explicit functions and modules over script-global side effects.
- Do not turn one-off scripts into mini-frameworks.
- Keep CLI parsing, IO, and business logic separated when the script is growing beyond a tiny helper.
- In Python text IO, pass `encoding="utf-8"` explicitly when reading or writing files unless binary IO is intended.
- Reuse existing fixtures, factories, tempdir helpers, HTTP clients, and app factories before adding new test infrastructure.

## Framework Guidance

### FastAPI / Flask / Django

- Follow the existing app factory, router/blueprint, settings, and dependency patterns.
- Keep request validation, domain logic, and persistence concerns separated when the repo already has those seams.
- Prefer framework-native testing helpers already in the repo.

### CLI / Script Work

- Prefer existing CLI surfaces such as `argparse`, `click`, or `typer` already used by the repo.
- Keep scripts idempotent when practical.
- Make destructive operations explicit and easy to review.
- Avoid hidden cwd assumptions when the script is likely to run from multiple locations.

## Verification

Prefer the smallest convincing check:

- targeted `pytest` scope for changed behavior
- targeted module or CLI invocation
- focused import or smoke check for packaging fixes
- broader test scope only when the blast radius requires it

If a repo has formatting or linting already configured, reuse it.
If no such tooling exists, do not invent new tooling just for this task.

## Output Expectations

When using this skill, state:

- the repo's Python environment or packaging assumption you followed
- the main files or module owners changed
- the focused verification run
- any environment uncertainty or deferred broader validation
