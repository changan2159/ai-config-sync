from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.errors import SyncError


@dataclass(frozen=True)
class PiPackagePaths:
    settings_path: Path
    agent_dir: Path
    npm_dir: Path
    package_json_path: Path
    package_lock_path: Path


def pi_package_paths(settings_path: Path) -> PiPackagePaths:
    resolved_settings = settings_path.expanduser().resolve()
    agent_dir = resolved_settings.parent
    npm_dir = agent_dir / "npm"
    return PiPackagePaths(
        settings_path=resolved_settings,
        agent_dir=agent_dir,
        npm_dir=npm_dir,
        package_json_path=npm_dir / "package.json",
        package_lock_path=npm_dir / "package-lock.json",
    )


def sync_pi_packages(
    *,
    settings_path: Path,
    packages: tuple[str, ...],
    previous_packages: list[str],
) -> dict[str, Any]:
    paths = pi_package_paths(settings_path)
    desired_specs = _dedupe_specs(packages)
    previous_specs = _dedupe_specs(previous_packages)
    desired_names = {_package_name(spec) for spec in desired_specs}
    declared_names = set(_declared_dependency_names(paths.package_json_path))
    installed_names = set(_installed_package_names(paths.npm_dir))
    to_install = [
        spec
        for spec in desired_specs
        if _package_name(spec) not in installed_names
    ]
    to_remove = [
        spec
        for spec in previous_specs
        if _package_name(spec) not in desired_names
        and (_package_name(spec) in declared_names or _package_name(spec) in installed_names)
    ]

    if to_install:
        _ensure_package_manifest(paths.package_json_path)
        _run_command(["npm", "install", "--no-fund", "--no-audit", *(_install_arg(spec) for spec in to_install)], cwd=paths.npm_dir)

    if to_remove:
        _ensure_package_manifest(paths.package_json_path)
        _run_command(["npm", "uninstall", "--no-fund", "--no-audit", *(_package_name(spec) for spec in to_remove)], cwd=paths.npm_dir)

    return {
        "installed": list(to_install),
        "removed": list(to_remove),
        "installed_package_names": _installed_package_names(paths.npm_dir),
    }


def _dedupe_specs(packages: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for package in packages:
        if package in seen:
            continue
        seen.add(package)
        result.append(package)
    return tuple(result)


def _package_name(spec: str) -> str:
    return spec[4:] if spec.startswith("npm:") else spec


def _install_arg(spec: str) -> str:
    return _package_name(spec)


def _declared_dependency_names(package_json_path: Path) -> list[str]:
    if not package_json_path.exists():
        return []
    data = json.loads(package_json_path.read_text(encoding="utf-8"))
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        return []
    return sorted(name for name in dependencies if isinstance(name, str))


def _installed_package_names(npm_dir: Path) -> list[str]:
    node_modules_dir = npm_dir / "node_modules"
    if not node_modules_dir.is_dir():
        return []
    package_names: list[str] = []
    for package_json_path in node_modules_dir.glob("*/package.json"):
        package_name = _read_package_name(package_json_path)
        if package_name is not None:
            package_names.append(package_name)
    for package_json_path in node_modules_dir.glob("@*/*/package.json"):
        package_name = _read_package_name(package_json_path)
        if package_name is not None:
            package_names.append(package_name)
    return sorted(set(package_names))


def _read_package_name(package_json_path: Path) -> str | None:
    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    package_name = data.get("name")
    return package_name if isinstance(package_name, str) and package_name else None


def _ensure_package_manifest(package_json_path: Path) -> None:
    if package_json_path.exists():
        return
    package_json_path.parent.mkdir(parents=True, exist_ok=True)
    package_json_path.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {},
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    if shutil.which(args[0]) is None:
        raise SyncError(f"Required command not found: {args[0]}")
    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}") from exc
