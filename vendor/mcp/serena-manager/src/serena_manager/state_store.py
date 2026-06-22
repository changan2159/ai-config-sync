from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any


@dataclass
class ProjectState:
    project_root: str
    project_hash: str
    transport: str
    endpoint_url: str
    serena_context: str
    pid: int
    started_at: float
    last_active_at: float
    status: str
    failure_count: int = 0
    last_error: str = ""


class StateStore:
    def __init__(self, state_root: Path) -> None:
        self.state_root = state_root
        self.state_root.mkdir(parents=True, exist_ok=True)

    def project_hash(self, project_root: Path) -> str:
        return hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:16]

    def project_dir(self, project_root: Path) -> Path:
        return self.state_root / self.project_hash(project_root)

    def meta_path(self, project_root: Path) -> Path:
        return self.project_dir(project_root) / "meta.json"

    def lock_path(self, project_root: Path) -> Path:
        return self.project_dir(project_root) / "lock"

    def manager_log_path(self, project_root: Path) -> Path:
        return self.project_dir(project_root) / "manager.log"

    def stdout_log_path(self, project_root: Path) -> Path:
        return self.project_dir(project_root) / "serena.stdout.log"

    def stderr_log_path(self, project_root: Path) -> Path:
        return self.project_dir(project_root) / "serena.stderr.log"

    def ensure_project_dir(self, project_root: Path) -> Path:
        directory = self.project_dir(project_root)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def load(self, project_root: Path) -> ProjectState | None:
        meta_path = self.meta_path(project_root)
        if not meta_path.is_file():
            return None
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except (JSONDecodeError, OSError):
            self._quarantine_corrupt_meta(meta_path)
            return None
        data.setdefault("serena_context", "codex")
        return ProjectState(**data)

    def save(self, state: ProjectState) -> None:
        project_root = Path(state.project_root)
        directory = self.ensure_project_dir(project_root)
        tmp_path = directory / "meta.json.tmp"
        tmp_path.write_text(json.dumps(asdict(state), indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(directory / "meta.json")

    def delete(self, project_root: Path) -> None:
        directory = self.project_dir(project_root)
        if not directory.exists():
            return
        for child in sorted(directory.iterdir()):
            if child.is_file() or child.is_symlink():
                child.unlink(missing_ok=True)
        try:
            directory.rmdir()
        except OSError:
            pass

    def touch_activity(self, state: ProjectState, at: float | None = None) -> ProjectState:
        state.last_active_at = at if at is not None else time.time()
        self.save(state)
        return state

    def list_states(self) -> list[ProjectState]:
        states: list[ProjectState] = []
        for meta_path in self.state_root.glob("*/meta.json"):
            try:
                data: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
                data.setdefault("serena_context", "codex")
                states.append(ProjectState(**data))
            except Exception:
                continue
        return states

    def _quarantine_corrupt_meta(self, meta_path: Path) -> None:
        corrupt_path = meta_path.with_name(f"meta.corrupt.{int(time.time())}.json")
        try:
            meta_path.replace(corrupt_path)
        except OSError:
            meta_path.unlink(missing_ok=True)
