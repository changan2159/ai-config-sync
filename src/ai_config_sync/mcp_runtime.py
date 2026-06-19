from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ai_config_sync.sync import SyncError


BOOTSTRAP_VERSION = "3"
RUNTIME_ENV_NAME = "runtime-env.sh"


@dataclass(frozen=True)
class ToolchainPaths:
    repo_root: Path
    toolchain_root: Path
    uv_root: Path
    uv_bin: Path
    python_install_root: Path
    python_root: Path
    python_bin: Path
    node_root: Path
    node_bin: Path
    npm_bin: Path
    runtime_env_path: Path


def preflight_mcp(repo_root: Path, components: Iterable[str] | None = None) -> dict[str, Any]:
    requested = _normalize_components(components)
    paths = _toolchain_paths(repo_root)
    lock = _load_toolchain_lock(repo_root)
    _ensure_supported_platform(lock)
    _prepare_uv_toolchain(paths, lock)
    _prepare_python_toolchain(paths, lock)
    _prepare_node_toolchain(paths, lock)
    _write_runtime_env(paths)

    runtime_results: dict[str, Any] = {}
    if "serena-agent" in requested:
        runtime_results["serena-agent"] = _prepare_serena_agent_runtime(repo_root, paths)
    if "serena-manager" in requested:
        runtime_results["serena-manager"] = _prepare_serena_manager_runtime(repo_root, paths)
    if "fetch" in requested:
        runtime_results["fetch"] = _prepare_fetch_runtime(repo_root, paths)
    if "codegraph" in requested:
        runtime_results["codegraph"] = _prepare_codegraph_runtime(repo_root, paths)
    if "node-repl-linux" in requested:
        runtime_results["node-repl-linux"] = _prepare_node_repl_runtime(repo_root, paths)

    return {
        "toolchain": {
            "uv": str(paths.uv_bin),
            "python": str(paths.python_bin),
            "node": str(paths.node_bin),
            "npm": str(paths.npm_bin),
            "runtime_env": str(paths.runtime_env_path),
            "bootstrap_version": BOOTSTRAP_VERSION,
            "versions": {
                "uv": lock["uv"]["version"],
                "python": lock["python"]["version"],
                "node": lock["node"]["version"],
            },
        },
        "runtime": runtime_results,
    }


def _normalize_components(components: Iterable[str] | None) -> tuple[str, ...]:
    if components is None:
        return ("serena-agent", "serena-manager", "fetch", "codegraph", "node-repl-linux")
    normalized = tuple(dict.fromkeys(components))
    valid = {"serena-agent", "serena-manager", "fetch", "codegraph", "node-repl-linux"}
    unknown = sorted(set(normalized) - valid)
    if unknown:
        raise SyncError(f"Unsupported MCP preflight components: {', '.join(unknown)}")
    return normalized


def _toolchain_paths(repo_root: Path) -> ToolchainPaths:
    lock = _load_toolchain_lock(repo_root)
    toolchain_root = repo_root / "vendor" / "toolchain"
    uv_root = toolchain_root / "uv" / "current"
    python_install_root = toolchain_root / "python"
    python_root = python_install_root / lock["python"]["distribution"]
    python_version = str(lock["python"]["version"])
    major_minor = ".".join(python_version.split(".")[:2])
    python_bin = python_root / "bin" / f"python{major_minor}"
    node_root = toolchain_root / "node" / "current"
    return ToolchainPaths(
        repo_root=repo_root,
        toolchain_root=toolchain_root,
        uv_root=uv_root,
        uv_bin=uv_root / "uv",
        python_install_root=python_install_root,
        python_root=python_root,
        python_bin=python_bin,
        node_root=node_root,
        node_bin=node_root / "bin" / "node",
        npm_bin=node_root / "bin" / "npm",
        runtime_env_path=toolchain_root / RUNTIME_ENV_NAME,
    )


def _load_toolchain_lock(repo_root: Path) -> dict[str, Any]:
    lock_path = repo_root / "toolchain.lock.json"
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SyncError(f"Invalid toolchain lock payload: {lock_path}")
    return payload


def _ensure_supported_platform(lock: Mapping[str, Any]) -> None:
    expected = lock["platform"]
    actual = f"{platform.system().lower()}-{platform.machine().lower()}"
    aliases = {"linux-amd64": "linux-x86_64", "linux-x64": "linux-x86_64"}
    actual = aliases.get(actual, actual)
    if actual != expected:
        raise SyncError(f"Unsupported host platform '{actual}', expected '{expected}' for repo-local MCP toolchain")


def _prepare_uv_toolchain(paths: ToolchainPaths, lock: Mapping[str, Any]) -> None:
    if paths.uv_bin.is_file():
        return
    _download_and_extract(
        url=lock["uv"]["url"],
        archive_root=lock["uv"]["archive_root"],
        destination=paths.uv_root,
        mode="r:gz",
    )


def _prepare_python_toolchain(paths: ToolchainPaths, lock: Mapping[str, Any]) -> None:
    if paths.python_bin.is_file():
        return
    paths.python_install_root.mkdir(parents=True, exist_ok=True)
    _run_command(
        [
            str(paths.uv_bin),
            "python",
            "install",
            "--install-dir",
            str(paths.python_install_root),
            lock["python"]["version"],
        ]
    )
    if not paths.python_bin.is_file():
        raise SyncError(f"Repo-local managed Python install did not produce {paths.python_bin}")


def _prepare_node_toolchain(paths: ToolchainPaths, lock: Mapping[str, Any]) -> None:
    if paths.node_bin.is_file() and paths.npm_bin.is_file():
        return
    _download_and_extract(
        url=lock["node"]["url"],
        archive_root=lock["node"]["archive_root"],
        destination=paths.node_root,
        mode="r:xz",
    )
    if not paths.node_bin.is_file() or not paths.npm_bin.is_file():
        raise SyncError(f"Repo-local managed Node toolchain did not produce {paths.node_root / 'bin'}")


def _write_runtime_env(paths: ToolchainPaths) -> None:
    content = "\n".join(
        [
            "#!/usr/bin/env bash",
            f"export AI_CONFIG_SYNC_TOOLCHAIN_BOOTSTRAP_VERSION={BOOTSTRAP_VERSION}",
            f"export AI_CONFIG_SYNC_TOOLCHAIN_UV={_shell_quote(str(paths.uv_bin))}",
            f"export AI_CONFIG_SYNC_TOOLCHAIN_PYTHON={_shell_quote(str(paths.python_bin))}",
            f"export AI_CONFIG_SYNC_TOOLCHAIN_NODE={_shell_quote(str(paths.node_bin))}",
            f"export AI_CONFIG_SYNC_TOOLCHAIN_NPM={_shell_quote(str(paths.npm_bin))}",
            "",
        ]
    )
    paths.runtime_env_path.parent.mkdir(parents=True, exist_ok=True)
    paths.runtime_env_path.write_text(content, encoding="utf-8")


def _prepare_serena_agent_runtime(repo_root: Path, paths: ToolchainPaths) -> dict[str, Any]:
    vendor_dir = repo_root / "vendor" / "mcp" / "serena-agent"
    venv_dir = vendor_dir / ".venv"
    python_bin = venv_dir / "bin" / "python"
    requirements_file = vendor_dir / "requirements.lock"
    stamp_file = vendor_dir / ".requirements.sha256"
    current_hash = _hash_files(
        (requirements_file,),
        salt=f"bootstrap-version={BOOTSTRAP_VERSION};python={paths.python_bin}",
    )
    if stamp_file.is_file() and stamp_file.read_text(encoding="utf-8") == current_hash and python_bin.is_file():
        return {"prepared": False, "reason": "up-to-date", "python": str(python_bin)}
    shutil.rmtree(venv_dir, ignore_errors=True)
    _run_command([str(paths.uv_bin), "venv", "--python", str(paths.python_bin), str(venv_dir)])
    _run_command([str(paths.uv_bin), "pip", "install", "--python", str(python_bin), "-r", str(requirements_file)])
    stamp_file.write_text(current_hash, encoding="utf-8")
    return {"prepared": True, "python": str(python_bin)}


def _prepare_serena_manager_runtime(repo_root: Path, paths: ToolchainPaths) -> dict[str, Any]:
    vendor_dir = repo_root / "vendor" / "mcp" / "serena-manager"
    venv_python = vendor_dir / ".venv" / "bin" / "python"
    stamp_file = vendor_dir / ".source.sha256"
    tracked_files = [
        vendor_dir / "pyproject.toml",
        vendor_dir / "uv.lock",
        *sorted((vendor_dir / "src" / "serena_manager").rglob("*.py")),
    ]
    current_hash = _hash_serena_manager_source(
        tracked_files,
        vendor_dir,
        salt=f"bootstrap-version={BOOTSTRAP_VERSION};python={paths.python_bin}",
    )
    if stamp_file.is_file() and stamp_file.read_text(encoding="utf-8") == current_hash and venv_python.is_file():
        return {"prepared": False, "reason": "up-to-date", "python": str(venv_python)}
    shutil.rmtree(vendor_dir / ".venv", ignore_errors=True)
    _run_command(
        [
            str(paths.uv_bin),
            "sync",
            "--frozen",
            "--no-dev",
            "--python",
            str(paths.python_bin),
        ],
        cwd=vendor_dir,
    )
    stamp_file.write_text(current_hash, encoding="utf-8")
    return {"prepared": True, "python": str(venv_python)}


def _prepare_fetch_runtime(repo_root: Path, paths: ToolchainPaths) -> dict[str, Any]:
    vendor_dir = repo_root / "vendor" / "mcp" / "fetch"
    venv_dir = vendor_dir / ".venv"
    fetch_bin = venv_dir / "bin" / "mcp-server-fetch"
    requirements_file = vendor_dir / "requirements.lock"
    stamp_file = vendor_dir / ".requirements.sha256"
    if not requirements_file.is_file():
        raise SyncError(f"Missing repo-local fetch lockfile: {requirements_file}")
    current_hash = _hash_files(
        (requirements_file,),
        salt=f"bootstrap-version={BOOTSTRAP_VERSION};python={paths.python_bin}",
    )
    if stamp_file.is_file() and stamp_file.read_text(encoding="utf-8") == current_hash and fetch_bin.is_file():
        return {"prepared": False, "reason": "up-to-date", "entrypoint": str(fetch_bin)}
    shutil.rmtree(venv_dir, ignore_errors=True)
    _run_command([str(paths.uv_bin), "venv", "--python", str(paths.python_bin), str(venv_dir)])
    _run_command([str(paths.uv_bin), "pip", "install", "--python", str(venv_dir / "bin" / "python"), "-r", str(requirements_file)])
    if not fetch_bin.is_file():
        raise SyncError(f"Repo-local fetch install did not produce {fetch_bin}")
    stamp_file.write_text(current_hash, encoding="utf-8")
    return {"prepared": True, "entrypoint": str(fetch_bin)}


def _prepare_codegraph_runtime(repo_root: Path, paths: ToolchainPaths) -> dict[str, Any]:
    vendor_dir = repo_root / "vendor" / "mcp" / "codegraph"
    bin_path = vendor_dir / "node_modules" / ".bin" / "codegraph"
    stamp_file = vendor_dir / ".package-lock.sha256"
    current_hash = _hash_files(
        (vendor_dir / "package-lock.json",),
        salt=f"bootstrap-version={BOOTSTRAP_VERSION};node={paths.node_bin}",
    )
    if stamp_file.is_file() and stamp_file.read_text(encoding="utf-8") == current_hash and bin_path.is_file():
        return {"prepared": False, "reason": "up-to-date", "entrypoint": str(bin_path)}
    shutil.rmtree(vendor_dir / "node_modules", ignore_errors=True)
    _run_command([str(paths.npm_bin), "ci", "--silent"], cwd=vendor_dir, env_overrides=_node_env(paths))
    stamp_file.write_text(current_hash, encoding="utf-8")
    return {"prepared": True, "entrypoint": str(bin_path)}


def _prepare_node_repl_runtime(repo_root: Path, paths: ToolchainPaths) -> dict[str, Any]:
    vendor_dir = repo_root / "vendor" / "mcp" / "node-repl-linux"
    stamp_file = vendor_dir / ".package-lock.sha256"
    current_hash = _hash_files(
        (vendor_dir / "package-lock.json",),
        salt=f"bootstrap-version={BOOTSTRAP_VERSION};node={paths.node_bin}",
    )
    if stamp_file.is_file() and stamp_file.read_text(encoding="utf-8") == current_hash and (vendor_dir / "node_modules").is_dir():
        return {"prepared": False, "reason": "up-to-date", "entrypoint": str(vendor_dir / "index.mjs")}
    shutil.rmtree(vendor_dir / "node_modules", ignore_errors=True)
    _run_command([str(paths.npm_bin), "ci", "--silent"], cwd=vendor_dir, env_overrides=_node_env(paths))
    stamp_file.write_text(current_hash, encoding="utf-8")
    return {"prepared": True, "entrypoint": str(vendor_dir / "index.mjs")}


def _download_and_extract(url: str, archive_root: str, destination: Path, mode: str) -> None:
    with tempfile.TemporaryDirectory(prefix="ai-config-sync-toolchain-") as temp_root_text:
        temp_root = Path(temp_root_text)
        archive_path = temp_root / "archive"
        request = urllib.request.Request(url, headers={"User-Agent": "ai-config-sync/0.1"})
        with urllib.request.urlopen(request, timeout=120) as response, archive_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
        extracted_root = temp_root / "extracted"
        extracted_root.mkdir()
        with tarfile.open(archive_path, mode) as archive:
            archive.extractall(extracted_root)
        source_root = extracted_root / archive_root
        if not source_root.exists():
            raise SyncError(f"Downloaded archive did not contain expected root '{archive_root}' from {url}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(destination, ignore_errors=True)
        shutil.move(str(source_root), str(destination))


def _hash_files(paths: Iterable[Path], *, salt: str) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    digest.update(salt.encode("utf-8"))
    return digest.hexdigest()


def _hash_serena_manager_source(paths: Iterable[Path], root: Path, *, salt: str) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(root)
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    digest.update(salt.encode("utf-8"))
    return digest.hexdigest()


def _node_env(paths: ToolchainPaths) -> dict[str, str]:
    env = dict(os.environ)
    node_bin_dir = str(paths.node_bin.parent)
    env["PATH"] = f"{node_bin_dir}{os.pathsep}{env.get('PATH', '')}" if env.get("PATH") else node_bin_dir
    return env


def _run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    env_overrides: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            env=dict(env_overrides) if env_overrides is not None else None,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"Required command not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}") from exc


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
