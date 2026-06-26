from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

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


def inspect_pi_packages(
    *,
    settings_path: Path,
    packages: tuple[str, ...],
    latest_version_resolver: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    paths = pi_package_paths(settings_path)
    managed_specs = _dedupe_specs(packages)
    declared = _declared_dependency_versions(paths.package_json_path)
    installed = _installed_package_versions(paths.npm_dir)
    entries: list[dict[str, Any]] = []
    for spec in managed_specs:
        name = _package_name(spec)
        installed_version = installed.get(name)
        latest_version = latest_version_resolver(name) if latest_version_resolver else None
        entries.append(
            {
                "spec": spec,
                "name": name,
                "declared_version": declared.get(name),
                "installed_version": installed_version,
                "latest_version": latest_version,
                "has_update": bool(installed_version and latest_version and installed_version != latest_version),
                "installed": name in installed,
            }
        )
    return {
        "settings_path": str(paths.settings_path),
        "npm_dir": str(paths.npm_dir),
        "package_json_path": str(paths.package_json_path),
        "managed_specs": list(managed_specs),
        "declared_dependencies": declared,
        "installed_package_versions": installed,
        "managed_entries": entries,
    }


def upgrade_pi_packages(
    *,
    settings_path: Path,
    packages: tuple[str, ...],
    target_specs: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    paths = pi_package_paths(settings_path)
    managed_specs = _dedupe_specs(packages)
    desired_specs = _dedupe_specs(target_specs or packages)
    if desired_specs:
        _ensure_package_manifest(paths.package_json_path)
        _run_command(
            ["npm", "install", "--no-fund", "--no-audit", *(_install_arg(spec) for spec in desired_specs)],
            cwd=paths.npm_dir,
        )
    result = inspect_pi_packages(settings_path=settings_path, packages=managed_specs)
    result["upgraded"] = list(desired_specs)
    return result


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
    return sorted(_declared_dependency_versions(package_json_path))


def _declared_dependency_versions(package_json_path: Path) -> dict[str, str]:
    if not package_json_path.exists():
        return {}
    data = json.loads(package_json_path.read_text(encoding="utf-8"))
    dependencies = data.get("dependencies", {})
    if not isinstance(dependencies, dict):
        return {}
    result: dict[str, str] = {}
    for name, version in dependencies.items():
        if isinstance(name, str) and name and isinstance(version, str):
            result[name] = version
    return result


def _installed_package_names(npm_dir: Path) -> list[str]:
    return sorted(_installed_package_versions(npm_dir))


def _installed_package_versions(npm_dir: Path) -> dict[str, str]:
    node_modules_dir = npm_dir / "node_modules"
    if not node_modules_dir.is_dir():
        return {}
    packages: dict[str, str] = {}
    for package_json_path in node_modules_dir.glob("*/package.json"):
        package = _read_package_metadata(package_json_path)
        if package is not None:
            packages[package["name"]] = package["version"]
    for package_json_path in node_modules_dir.glob("@*/*/package.json"):
        package = _read_package_metadata(package_json_path)
        if package is not None:
            packages[package["name"]] = package["version"]
    return dict(sorted(packages.items()))


def _read_package_name(package_json_path: Path) -> str | None:
    package = _read_package_metadata(package_json_path)
    return package["name"] if package is not None else None


def _read_package_metadata(package_json_path: Path) -> dict[str, str] | None:
    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    package_name = data.get("name")
    package_version = data.get("version")
    if not isinstance(package_name, str) or not package_name:
        return None
    version = package_version if isinstance(package_version, str) and package_version else "unknown"
    return {"name": package_name, "version": version}


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
