from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ai_config_sync.mcp_runtime import preflight_mcp
from ai_config_sync.sync import SyncError


SERENA_AGENT_PACKAGE = "serena-agent"
SERENA_AGENT_VENDORED_PACKAGES = ("serena", "interprompt", "solidlsp")
SERENA_AGENT_LOCK_EXCLUDES = frozenset({"serena-agent", "interprompt", "solidlsp"})
CODEGRAPH_PACKAGE = "@colbymchenry/codegraph"
NODE_REPL_DEPENDENCIES = ("@modelcontextprotocol/sdk", "zod")
FETCH_PACKAGE = "mcp-server-fetch"


def update_serena_agent(repo_root: Path, version: str | None = None) -> dict[str, Any]:
    vendor_dir = _require_vendor_dir(repo_root, "serena-agent")
    resolved_version = version or _latest_pypi_version(SERENA_AGENT_PACKAGE)
    toolchain = _prepare_update_toolchain(repo_root)
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-serena-agent-") as temp_root_text:
        temp_root = Path(temp_root_text)
        venv_dir = temp_root / "venv"
        _run_command([toolchain["uv"], "venv", str(venv_dir)])
        python_bin = _venv_python(venv_dir)
        _run_command(
            [
                toolchain["uv"],
                "pip",
                "install",
                "--python",
                str(python_bin),
                f"{SERENA_AGENT_PACKAGE}=={resolved_version}",
            ]
        )
        site_packages = _site_packages(python_bin)
        staged_vendor_dir = temp_root / "staged-serena-agent"
        for package_name in SERENA_AGENT_VENDORED_PACKAGES:
            _replace_path(site_packages / package_name, staged_vendor_dir / "pylib" / package_name)
        dist_info_source = _find_single_path(site_packages, "serena_agent-*.dist-info")
        _replace_path(dist_info_source, staged_vendor_dir / "upstream-dist-info")
        lock_text = _filtered_requirements_lock(toolchain["uv"], python_bin)
        (staged_vendor_dir / "requirements.lock").write_text(lock_text, encoding="utf-8")
        _commit_replaced_paths(
            [
                (staged_vendor_dir / "pylib", vendor_dir / "pylib"),
                (staged_vendor_dir / "upstream-dist-info", vendor_dir / "upstream-dist-info"),
                (staged_vendor_dir / "requirements.lock", vendor_dir / "requirements.lock"),
            ],
            temp_root / "commit-backup",
        )
    return {
        "name": "serena-agent",
        "version": resolved_version,
        "packages": list(SERENA_AGENT_VENDORED_PACKAGES),
        "requirements_path": str(vendor_dir / "requirements.lock"),
        "preflight": preflight_mcp(repo_root, components=["serena-agent"])["runtime"]["serena-agent"],
    }


def update_codegraph(repo_root: Path, version: str | None = None) -> dict[str, Any]:
    vendor_dir = _require_vendor_dir(repo_root, "codegraph")
    toolchain = _prepare_update_toolchain(repo_root)
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-codegraph-") as temp_root_text:
        staged_dir = _stage_npm_vendor_dir(vendor_dir, Path(temp_root_text))
        package_path = staged_dir / "package.json"
        payload = _read_json(package_path)
        previous_version = _require_dependency(payload, CODEGRAPH_PACKAGE, package_path)
        resolved_version = version or _latest_npm_version(CODEGRAPH_PACKAGE)
        payload["dependencies"][CODEGRAPH_PACKAGE] = resolved_version
        _write_json(package_path, payload)
        _run_command(
            [toolchain["npm"], "install", "--package-lock-only", "--ignore-scripts"],
            cwd=staged_dir,
            env_overrides=_node_tool_env(toolchain["node"]),
        )
        _commit_replaced_paths(
            [
                (staged_dir / "package.json", vendor_dir / "package.json"),
                (staged_dir / "package-lock.json", vendor_dir / "package-lock.json"),
            ],
            Path(temp_root_text) / "commit-backup",
        )
    return {
        "name": "codegraph",
        "version": resolved_version,
        "previous_version": previous_version,
        "package": CODEGRAPH_PACKAGE,
        "preflight": preflight_mcp(repo_root, components=["codegraph"])["runtime"]["codegraph"],
    }


def update_node_repl_linux(
    repo_root: Path,
    sdk_version: str | None = None,
    zod_version: str | None = None,
) -> dict[str, Any]:
    vendor_dir = _require_vendor_dir(repo_root, "node-repl-linux")
    toolchain = _prepare_update_toolchain(repo_root)
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-node-repl-") as temp_root_text:
        staged_dir = _stage_npm_vendor_dir(vendor_dir, Path(temp_root_text))
        package_path = staged_dir / "package.json"
        payload = _read_json(package_path)
        dependency_updates = {
            "@modelcontextprotocol/sdk": sdk_version or _latest_npm_version("@modelcontextprotocol/sdk"),
            "zod": zod_version or _latest_npm_version("zod"),
        }
        changes: dict[str, dict[str, str]] = {}
        for dependency_name, resolved_version in dependency_updates.items():
            previous_version = _require_dependency(payload, dependency_name, package_path)
            payload["dependencies"][dependency_name] = resolved_version
            changes[dependency_name] = {"from": previous_version, "to": resolved_version}
        _write_json(package_path, payload)
        _run_command(
            [toolchain["npm"], "install", "--package-lock-only", "--ignore-scripts"],
            cwd=staged_dir,
            env_overrides=_node_tool_env(toolchain["node"]),
        )
        _commit_replaced_paths(
            [
                (staged_dir / "package.json", vendor_dir / "package.json"),
                (staged_dir / "package-lock.json", vendor_dir / "package-lock.json"),
            ],
            Path(temp_root_text) / "commit-backup",
        )
    return {
        "name": "node-repl-linux",
        "dependencies": changes,
        "managed_dependencies": list(NODE_REPL_DEPENDENCIES),
        "preflight": preflight_mcp(repo_root, components=["node-repl-linux"])["runtime"]["node-repl-linux"],
    }


def update_fetch(repo_root: Path, version: str | None = None) -> dict[str, Any]:
    vendor_dir = _require_vendor_dir(repo_root, "fetch")
    resolved_version = version or _latest_pypi_version(FETCH_PACKAGE)
    toolchain = _prepare_update_toolchain(repo_root)
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-fetch-") as temp_root_text:
        temp_root = Path(temp_root_text)
        venv_dir = temp_root / "venv"
        _run_command([toolchain["uv"], "venv", str(venv_dir)])
        python_bin = _venv_python(venv_dir)
        _run_command(
            [
                toolchain["uv"],
                "pip",
                "install",
                "--python",
                str(python_bin),
                f"{FETCH_PACKAGE}=={resolved_version}",
            ]
        )
        lock_text = _run_command([toolchain["uv"], "pip", "freeze", "--python", str(python_bin)]).stdout
        staged_lock_path = temp_root / "requirements.lock"
        staged_lock_path.write_text(lock_text, encoding="utf-8")
        _commit_replaced_paths(
            [(staged_lock_path, vendor_dir / "requirements.lock")],
            temp_root / "commit-backup",
        )
    return {
        "name": "fetch",
        "version": resolved_version,
        "package": FETCH_PACKAGE,
        "requirements_path": str(vendor_dir / "requirements.lock"),
        "preflight": preflight_mcp(repo_root, components=["fetch"])["runtime"]["fetch"],
    }


def update_all_mcp(
    repo_root: Path,
    *,
    serena_agent_version: str | None = None,
    fetch_version: str | None = None,
    codegraph_version: str | None = None,
    sdk_version: str | None = None,
    zod_version: str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-update-all-") as temp_root_text:
        snapshots = _snapshot_paths(_update_all_paths(repo_root), Path(temp_root_text))
        try:
            updated = [
                update_serena_agent(repo_root, version=serena_agent_version),
                update_fetch(repo_root, version=fetch_version),
                update_codegraph(repo_root, version=codegraph_version),
                update_node_repl_linux(repo_root, sdk_version=sdk_version, zod_version=zod_version),
            ]
        except Exception:
            _restore_snapshots(snapshots)
            raise
    return {
        "updated": updated,
        "preflight": preflight_mcp(repo_root),
        "serena_manager": {
            "name": "serena-manager",
            "mode": "repo-local-manual",
            "updated": False,
        },
    }


def _run_command(
    args: list[str],
    cwd: Path | None = None,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=dict(env_overrides) if env_overrides is not None else None,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"Required command not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}") from exc


def _require_vendor_dir(repo_root: Path, name: str) -> Path:
    vendor_dir = repo_root / "vendor" / "mcp" / name
    if not vendor_dir.is_dir():
        raise SyncError(f"Missing repo-local MCP source: {vendor_dir}")
    return vendor_dir


def _require_dependency(payload: dict[str, Any], name: str, package_path: Path) -> str:
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict) or name not in dependencies:
        raise SyncError(f"Missing dependency '{name}' in {package_path}")
    version = dependencies[name]
    if not isinstance(version, str) or not version.strip():
        raise SyncError(f"Invalid dependency version for '{name}' in {package_path}")
    return version


def _prepare_update_toolchain(repo_root: Path) -> dict[str, str]:
    payload = preflight_mcp(repo_root, components=[])
    toolchain = payload.get("toolchain")
    if not isinstance(toolchain, dict):
        raise SyncError("MCP preflight did not return a toolchain payload")
    required_keys = ("uv", "npm", "node")
    result: dict[str, str] = {}
    for key in required_keys:
        value = toolchain.get(key)
        if not isinstance(value, str) or not value.strip():
            raise SyncError(f"MCP preflight did not return toolchain path '{key}'")
        result[key] = value
    return result


def _node_tool_env(node_bin: str) -> dict[str, str]:
    env = dict(os.environ)
    node_bin_dir = str(Path(node_bin).parent)
    env["PATH"] = f"{node_bin_dir}{os.pathsep}{env.get('PATH', '')}" if env.get("PATH") else node_bin_dir
    return env


def _latest_pypi_version(package_name: str) -> str:
    payload = _fetch_json(f"https://pypi.org/pypi/{urllib.parse.quote(package_name)}/json")
    version = payload.get("info", {}).get("version")
    if not isinstance(version, str) or not version.strip():
        raise SyncError(f"Unable to resolve latest PyPI version for {package_name}")
    return version


def _latest_npm_version(package_name: str) -> str:
    encoded_name = urllib.parse.quote(package_name, safe="")
    payload = _fetch_json(f"https://registry.npmjs.org/{encoded_name}")
    version = payload.get("dist-tags", {}).get("latest")
    if not isinstance(version, str) or not version.strip():
        raise SyncError(f"Unable to resolve latest npm version for {package_name}")
    return version


def _fetch_json(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise SyncError(f"Failed to fetch metadata from {url}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SyncError(f"Unexpected metadata payload from {url}")
    return payload


def _venv_python(venv_dir: Path) -> Path:
    python_bin = venv_dir / "bin" / "python"
    if not python_bin.is_file():
        raise SyncError(f"Python virtualenv bootstrap failed: {python_bin}")
    return python_bin


def _site_packages(python_bin: Path) -> Path:
    result = _run_command(
        [
            str(python_bin),
            "-c",
            "import sysconfig; print(sysconfig.get_paths()['purelib'])",
        ]
    )
    site_packages = Path(result.stdout.strip())
    if not site_packages.is_dir():
        raise SyncError(f"Unable to locate site-packages for {python_bin}")
    return site_packages


def _find_single_path(root: Path, pattern: str) -> Path:
    matches = sorted(root.glob(pattern))
    if len(matches) != 1:
        raise SyncError(f"Expected one match for {pattern} under {root}, found {len(matches)}")
    return matches[0]


def _update_all_paths(repo_root: Path) -> list[Path]:
    serena_vendor_dir = _require_vendor_dir(repo_root, "serena-agent")
    fetch_vendor_dir = _require_vendor_dir(repo_root, "fetch")
    codegraph_vendor_dir = _require_vendor_dir(repo_root, "codegraph")
    node_repl_vendor_dir = _require_vendor_dir(repo_root, "node-repl-linux")
    return [
        serena_vendor_dir / "pylib",
        serena_vendor_dir / "upstream-dist-info",
        serena_vendor_dir / "requirements.lock",
        fetch_vendor_dir / "requirements.lock",
        codegraph_vendor_dir / "package.json",
        codegraph_vendor_dir / "package-lock.json",
        node_repl_vendor_dir / "package.json",
        node_repl_vendor_dir / "package-lock.json",
    ]


def _snapshot_paths(paths: list[Path], temp_root: Path) -> dict[Path, Path | None]:
    snapshots: dict[Path, Path | None] = {}
    for index, path in enumerate(paths):
        if not path.exists() and not path.is_symlink():
            snapshots[path] = None
            continue
        snapshot_path = temp_root / f"{index}-{path.name}"
        path_parent = snapshot_path.parent
        path_parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir() and not path.is_symlink():
            shutil.copytree(path, snapshot_path)
        else:
            shutil.copy2(path, snapshot_path)
        snapshots[path] = snapshot_path
    return snapshots


def _restore_snapshots(snapshots: dict[Path, Path | None]) -> None:
    for destination, snapshot_path in snapshots.items():
        _remove_path(destination)
        if snapshot_path is None:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        if snapshot_path.is_dir():
            shutil.copytree(snapshot_path, destination)
        else:
            shutil.copy2(snapshot_path, destination)


def _stage_npm_vendor_dir(vendor_dir: Path, temp_root: Path) -> Path:
    staged_dir = temp_root / vendor_dir.name
    shutil.copytree(vendor_dir, staged_dir, ignore=shutil.ignore_patterns("node_modules"))
    return staged_dir


def _commit_replaced_paths(replacements: list[tuple[Path, Path]], backup_root: Path) -> None:
    backup_root.mkdir(parents=True, exist_ok=True)
    backups: list[tuple[Path, Path]] = []
    written_destinations: list[Path] = []
    try:
        for index, (_source, destination) in enumerate(replacements):
            if destination.exists() or destination.is_symlink():
                backup_path = backup_root / f"{index}-{destination.name}"
                shutil.move(str(destination), str(backup_path))
                backups.append((backup_path, destination))
        for source, destination in replacements:
            if not source.exists():
                raise SyncError(f"Missing staged path: {source}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)
            written_destinations.append(destination)
    except Exception:
        for destination in reversed(written_destinations):
            _remove_path(destination)
        for backup_path, destination in reversed(backups):
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(backup_path), str(destination))
        raise


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    if path.is_dir():
        shutil.rmtree(path)


def _replace_path(source: Path, destination: Path) -> None:
    if not source.exists():
        raise SyncError(f"Missing expected source path: {source}")
    if destination.exists() or destination.is_symlink():
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def _filtered_requirements_lock(uv_bin: str, python_bin: Path) -> str:
    result = _run_command([uv_bin, "pip", "freeze", "--python", str(python_bin), "--exclude-editable"])
    lines: list[str] = []
    for line in result.stdout.splitlines():
        requirement = line.strip()
        if not requirement:
            continue
        normalized = _normalize_requirement_name(requirement)
        if normalized in SERENA_AGENT_LOCK_EXCLUDES:
            continue
        lines.append(requirement)
    return "\n".join(lines) + "\n"


def _normalize_requirement_name(requirement: str) -> str:
    if " @ " in requirement:
        name = requirement.split(" @ ", 1)[0]
    elif "==" in requirement:
        name = requirement.split("==", 1)[0]
    else:
        name = requirement
    return name.strip().lower().replace("_", "-")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SyncError(f"Expected JSON object in {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
