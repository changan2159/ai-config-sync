from __future__ import annotations

import argparse
import json

from serena_manager.config import ManagerConfig
from serena_manager.manager import SerenaManager
from serena_manager.paths import discover_repo_root
from serena_manager.project_root import detect_project_root
from serena_manager.reaper import Reaper


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="serena-manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--project", required=True)

    cleanup_parser = subparsers.add_parser("cleanup")
    cleanup_parser.add_argument("--project", required=False)

    reap_parser = subparsers.add_parser("reap")
    reap_parser.add_argument("--once", action="store_true")

    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--project", required=False)

    return parser


def main() -> None:
    repo_root = discover_repo_root()
    config = ManagerConfig.default(repo_root)
    manager = SerenaManager(config)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "status":
        print(json.dumps(manager.status(), indent=2, ensure_ascii=False))
        return
    if args.command == "stop":
        project_root = detect_project_root(args.project)
        result = manager.stop(project_root)
        print(json.dumps({"stopped": result, "project_root": str(project_root)}, ensure_ascii=False))
        return
    if args.command == "cleanup":
        if args.project:
            project_root = detect_project_root(args.project)
            result = manager.stop(project_root)
            print(json.dumps({"cleaned": [str(project_root)] if result else []}, ensure_ascii=False))
            return
        print(json.dumps({"cleaned": manager.cleanup()}, ensure_ascii=False))
        return
    if args.command == "reap":
        result = Reaper(manager).reap_once()
        print(
            json.dumps(
                {
                    "cleaned_unhealthy": result.cleaned_unhealthy,
                    "cleaned_idle": result.cleaned_idle,
                },
                ensure_ascii=False,
            )
        )
        return
    if args.command == "doctor":
        project_root = detect_project_root(args.project) if args.project else None
        print(json.dumps(manager.doctor(project_root), indent=2, ensure_ascii=False))
        return
    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
