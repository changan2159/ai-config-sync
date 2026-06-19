from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable

from ai_config_sync.sync import (
    McpServerConfig,
    SyncError,
    add_mcp_server,
    default_paths,
    install_service,
    load_sync_config,
    remove_mcp_server,
    service_status,
    start_service,
    stop_service,
    sync_clients,
    watch_loop,
)


def _parse_pairs(entries: list[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in entries:
        if "=" not in entry:
            raise SyncError(f"Invalid {label} entry '{entry}', expected KEY=value")
        key, value = entry.split("=", 1)
        result[key] = value
    return result


def _looks_like_repo_root(path: Path) -> bool:
    return (path / "shared-ai-config.json").is_file() and (path / "pyproject.toml").is_file()


def _iter_candidate_dirs(path: Path) -> list[Path]:
    resolved = path.resolve()
    start = resolved if resolved.is_dir() else resolved.parent
    return [start, *start.parents]


def _resolve_repo_root(
    entrypoint: Path | None = None,
    module_path: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    candidates = [
        entrypoint or Path(sys.argv[0]),
        cwd or Path.cwd(),
        module_path or Path(__file__),
    ]
    for candidate in candidates:
        for directory in _iter_candidate_dirs(candidate):
            if _looks_like_repo_root(directory):
                return directory
    return Path(__file__).resolve().parents[2]


def _run_config_update(
    paths: Any,
    update: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    original_text = paths.config_path.read_text(encoding="utf-8") if paths.config_path.exists() else None
    snapshots: dict[Path, bytes | None] = {}
    try:
        result = update(paths.config_path)
        config = load_sync_config(paths.config_path)
        snapshots = _snapshot_managed_files(config, paths.state_path)
        result["sync"] = sync_clients(config, paths.state_path)
        return result
    except Exception:
        if original_text is None:
            paths.config_path.unlink(missing_ok=True)
        else:
            _atomic_write_text(paths.config_path, original_text)
        _restore_managed_files(snapshots)
        raise


def _managed_output_paths(config: Any, state_path: Path) -> list[Path]:
    paths: list[Path] = [state_path]
    for target in (config.codex, config.claude, config.opencode):
        if target is None:
            continue
        paths.append(target.config_path)
        prompt_path = getattr(target, "global_prompt_path", None)
        if prompt_path is not None:
            paths.append(prompt_path)
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        write_target = path.resolve() if path.is_symlink() else path
        if write_target in seen:
            continue
        seen.add(write_target)
        unique_paths.append(write_target)
    return unique_paths


def _snapshot_managed_files(config: Any, state_path: Path) -> dict[Path, bytes | None]:
    return {
        path: path.read_bytes() if path.exists() else None
        for path in _managed_output_paths(config, state_path)
    }


def _restore_managed_files(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if content is None:
            path.unlink(missing_ok=True)
            continue
        _atomic_write_bytes(path, content)


def _atomic_write_text(path: Path, content: str) -> None:
    _atomic_write_bytes(path, content.encode("utf-8"))


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
    try:
        temp_path.write_bytes(content)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-config-sync")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_once = subparsers.add_parser("sync-once")
    sync_once.add_argument("--config", required=False)

    sync_watch = subparsers.add_parser("sync-watch")
    sync_watch.add_argument("--config", required=False)
    sync_watch.add_argument("--interval", type=float, default=2.0)

    service_install = subparsers.add_parser("sync-service-install")
    service_install.add_argument("--config", required=False)
    service_install.add_argument("--interval", type=float, default=2.0)

    service_start = subparsers.add_parser("sync-service-start")
    service_start.add_argument("--config", required=False)
    service_start.add_argument("--interval", type=float, default=2.0)

    service_status_parser = subparsers.add_parser("sync-service-status")
    service_status_parser.add_argument("--config", required=False)

    service_stop = subparsers.add_parser("sync-service-stop")
    service_stop.add_argument("--config", required=False)

    mcp_add = subparsers.add_parser("mcp-add")
    mcp_add.add_argument("name")
    mcp_add.add_argument("--transport", choices=["stdio", "http", "sse"], default="stdio")
    mcp_add.add_argument("--server-command", dest="server_command", required=False)
    mcp_add.add_argument("--arg", action="append", default=[])
    mcp_add.add_argument("--cwd", required=False)
    mcp_add.add_argument("--env", action="append", default=[])
    mcp_add.add_argument("--url", required=False)
    mcp_add.add_argument("--header", action="append", default=[])
    mcp_add.add_argument("--tool-timeout", type=int, required=False)
    mcp_add.add_argument("--disabled", action="store_true")
    mcp_add.add_argument("--config", required=False)

    mcp_remove = subparsers.add_parser("mcp-remove")
    mcp_remove.add_argument("name")
    mcp_remove.add_argument("--config", required=False)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = _resolve_repo_root()
    paths = default_paths(repo_root, Path(args.config) if hasattr(args, "config") and args.config else None)
    try:
        if args.command == "sync-once":
            print(json.dumps(sync_clients(load_sync_config(paths.config_path), paths.state_path), indent=2, ensure_ascii=False))
            return
        if args.command == "sync-watch":
            watch_loop(paths, args.interval)
            return
        if args.command == "sync-service-install":
            print(json.dumps(install_service(paths, args.interval), indent=2, ensure_ascii=False))
            return
        if args.command == "sync-service-start":
            print(json.dumps(start_service(paths, args.interval), indent=2, ensure_ascii=False))
            return
        if args.command == "sync-service-status":
            print(json.dumps(service_status(paths), indent=2, ensure_ascii=False))
            return
        if args.command == "sync-service-stop":
            print(json.dumps(stop_service(paths), indent=2, ensure_ascii=False))
            return
        if args.command == "mcp-add":
            env = _parse_pairs(args.env, "env")
            headers = _parse_pairs(args.header, "header")
            result = _run_config_update(
                paths,
                lambda config_path: add_mcp_server(
                    config_path,
                    McpServerConfig(
                        name=args.name,
                        transport=args.transport,
                        command=args.server_command,
                        args=tuple(args.arg),
                        cwd=args.cwd,
                        env=env or None,
                        url=args.url,
                        headers=headers or None,
                        tool_timeout_sec=args.tool_timeout,
                        enabled=not args.disabled,
                    ),
                ),
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        if args.command == "mcp-remove":
            result = _run_config_update(paths, lambda config_path: remove_mcp_server(config_path, args.name))
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        parser.error(f"Unknown command: {args.command}")
    except SyncError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
