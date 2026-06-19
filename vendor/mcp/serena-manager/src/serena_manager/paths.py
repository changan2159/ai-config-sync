from __future__ import annotations

from pathlib import Path


def discover_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    for directory in (current.parent, *current.parents):
        if (directory / "pyproject.toml").is_file() and (directory / "src" / "serena_manager").is_dir():
            return directory
    raise RuntimeError("Unable to locate serena-manager repository root")

