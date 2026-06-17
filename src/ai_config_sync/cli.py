from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    repo_root = Path(__file__).resolve().parents[2]
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
            result = add_mcp_server(
                paths.config_path,
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
            )
            result["sync"] = sync_clients(load_sync_config(paths.config_path), paths.state_path)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        if args.command == "mcp-remove":
            result = remove_mcp_server(paths.config_path, args.name)
            result["sync"] = sync_clients(load_sync_config(paths.config_path), paths.state_path)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        parser.error(f"Unknown command: {args.command}")
    except SyncError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
