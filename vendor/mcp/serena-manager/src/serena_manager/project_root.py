from __future__ import annotations

from pathlib import Path


def detect_project_root(cwd: str | Path) -> Path:
    current = Path(cwd).resolve()

    for directory in (current, *current.parents):
        if (directory / ".serena" / "project.yml").is_file():
            return directory

    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory

    for directory in (current, *current.parents):
        if (directory / "AGENTS.md").is_file():
            return directory

    return current

