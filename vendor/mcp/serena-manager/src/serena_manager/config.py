from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_SERENA_ARGS = ("start-mcp-server",)


@dataclass(frozen=True)
class ManagerConfig:
    state_root: Path
    idle_timeout_seconds: int = 20 * 60
    startup_timeout_seconds: int = 45
    healthcheck_timeout_seconds: int = 10
    failure_backoff_seconds: int = 60
    context: str = "desktop-app"
    host: str = "127.0.0.1"
    serena_command: str = ""
    serena_args: tuple[str, ...] = DEFAULT_SERENA_ARGS

    @classmethod
    def default(cls, root: Path) -> "ManagerConfig":
        repo_root = root.resolve().parents[2]
        return cls(
            state_root=root / "state",
            serena_command=str(repo_root / "tools" / "mcp" / "serena-agent.sh"),
        )
