from __future__ import annotations

from dataclasses import dataclass

from serena_manager.manager import SerenaManager


@dataclass
class ReapResult:
    cleaned_unhealthy: list[str]
    cleaned_idle: list[str]


class Reaper:
    def __init__(self, manager: SerenaManager) -> None:
        self.manager = manager

    def reap_once(self) -> ReapResult:
        unhealthy = self.manager.cleanup()
        idle = self.manager.reap_idle()
        return ReapResult(cleaned_unhealthy=unhealthy, cleaned_idle=idle)

