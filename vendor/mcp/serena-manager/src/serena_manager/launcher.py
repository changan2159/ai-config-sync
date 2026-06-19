from __future__ import annotations

import argparse
from pathlib import Path

import anyio
from mcp.client.streamable_http import streamable_http_client
from mcp.server.stdio import stdio_server

from serena_manager.bridge import bridge_streams
from serena_manager.config import ManagerConfig
from serena_manager.manager import SerenaManager
from serena_manager.paths import discover_repo_root
from serena_manager.project_root import detect_project_root


async def _keepalive(manager: SerenaManager, state_project_root: Path) -> None:
    while True:
        state = manager.store.load(state_project_root)
        if state is None:
            return
        manager.store.touch_activity(state)
        await anyio.sleep(30)


async def run_launcher(cwd: str | None = None) -> None:
    repo_root = discover_repo_root()
    config = ManagerConfig.default(repo_root)
    manager = SerenaManager(config)
    effective_cwd = Path(cwd).resolve() if cwd else Path.cwd().resolve()
    project_root = detect_project_root(effective_cwd)
    manager._log(project_root, f"launcher start cwd={effective_cwd}")
    state = manager.ensure_instance(project_root)
    manager._log(project_root, f"launcher connected target pid={state.pid} endpoint={state.endpoint_url}")

    async with stdio_server() as (upstream_read, upstream_write):
        async with streamable_http_client(state.endpoint_url, terminate_on_close=False) as (
            downstream_read,
            downstream_write,
            _,
        ):
            async with anyio.create_task_group() as tg:
                tg.start_soon(_keepalive, manager, project_root)
                manager._log(project_root, "bridge start")
                await bridge_streams(upstream_read, upstream_write, downstream_read, downstream_write)
                manager._log(project_root, "bridge stop")


def main() -> None:
    parser = argparse.ArgumentParser(prog="serena-manager-launcher")
    parser.add_argument("--cwd", required=False)
    args = parser.parse_args()
    anyio.run(lambda: run_launcher(cwd=args.cwd))


if __name__ == "__main__":
    main()
