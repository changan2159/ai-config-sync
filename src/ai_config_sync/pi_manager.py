from __future__ import annotations

import json
import os
import pwd
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.errors import SyncError


PI_PACKAGE_NAME = "@earendil-works/pi-coding-agent"
DEFAULT_PI_INSTALL_PREFIX = ".local"
NPM_INSTALL_MAX_ATTEMPTS = 5
NPM_INSTALL_TIMEOUT_SECONDS = 300
NPM_FETCH_ARGS = (
    "--fetch-retries",
    "5",
    "--fetch-retry-mintimeout",
    "2000",
    "--fetch-retry-maxtimeout",
    "30000",
    "--fetch-timeout",
    "300000",
)


@dataclass(frozen=True)
class PiPaths:
    target_user: str
    target_uid: int
    home: Path
    prefix_dir: Path
    bin_dir: Path
    launcher_path: Path


def default_pi_paths(home: Path | None = None) -> PiPaths:
    account = _target_account()
    resolved_home = Path(home or account.pw_dir).expanduser().resolve()
    prefix_dir = resolved_home / DEFAULT_PI_INSTALL_PREFIX
    return PiPaths(
        target_user=account.pw_name,
        target_uid=account.pw_uid,
        home=resolved_home,
        prefix_dir=prefix_dir,
        bin_dir=prefix_dir / "bin",
        launcher_path=prefix_dir / "bin" / "pi",
    )


def install_pi(home: Path | None = None, version: str | None = None) -> dict[str, Any]:
    paths = default_pi_paths(home)
    _require_non_root_runtime_install(paths)
    package_spec = _package_spec(version)
    _install_pi_package(paths.prefix_dir, package_spec)
    version_output = _run_command([str(paths.launcher_path), "--version"]).stdout.strip()
    installed_version = _parse_installed_version(version_output)
    expected_version = version.strip() if version is not None else None
    if expected_version is not None and installed_version != expected_version:
        raise SyncError(
            f"Managed pi version check failed: expected '{expected_version}', got '{installed_version or '<empty>'}'"
        )
    return {
        "package": package_spec,
        "version": installed_version,
        "version_output": version_output,
        "launcher_path": str(paths.launcher_path),
        "install_prefix": str(paths.prefix_dir),
    }


def pi_status(home: Path | None = None) -> dict[str, Any]:
    paths = default_pi_paths(home)
    version_output: str | None = None
    version: str | None = None
    version_exit_code: int | None = None
    if paths.launcher_path.exists():
        version_proc = _run_command([str(paths.launcher_path), "--version"], check=False)
        version_output = version_proc.stdout.strip() or version_proc.stderr.strip() or None
        version_exit_code = version_proc.returncode
        if version_proc.returncode == 0 and version_output:
            version = _parse_installed_version(version_output)
    return {
        "launcher_path": str(paths.launcher_path),
        "launcher_exists": paths.launcher_path.exists(),
        "version": version,
        "version_output": version_output,
        "version_exit_code": version_exit_code,
        "install_prefix": str(paths.prefix_dir),
    }


def _target_account() -> pwd.struct_passwd:
    sudo_user = os.environ.get("SUDO_USER")
    if os.geteuid() == 0 and sudo_user and sudo_user != "root":
        return pwd.getpwnam(sudo_user)
    return pwd.getpwuid(os.getuid())


def _package_spec(version: str | None) -> str:
    cleaned = version.strip() if version is not None else ""
    return f"{PI_PACKAGE_NAME}@{cleaned}" if cleaned else PI_PACKAGE_NAME


def _parse_installed_version(output: str) -> str:
    cleaned = output.strip()
    if not cleaned:
        raise SyncError("Unexpected pi version output: <empty>")
    if cleaned.startswith("pi "):
        return cleaned.split()[-1].removeprefix("v")
    if cleaned.startswith("v"):
        return cleaned.removeprefix("v")
    if re.fullmatch(r"\d+\.\d+(?:\.\d+)*", cleaned):
        return cleaned
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SyncError(f"Unexpected pi version output: {cleaned}") from exc
    version = payload.get("version")
    if isinstance(version, str) and version.strip():
        return version.strip().removeprefix("v")
    raise SyncError(f"Unexpected pi version output: {cleaned}")


def _require_non_root_runtime_install(paths: PiPaths) -> None:
    if os.geteuid() == 0 and paths.target_user != "root":
        raise SyncError(
            "pi-install must run as the target login user so the runtime under "
            f"{paths.home} stays user-owned"
        )


def _install_pi_package(prefix_dir: Path, package_spec: str) -> None:
    install_args = [
        "npm",
        "install",
        "-g",
        "--ignore-scripts",
        "--prefix",
        str(prefix_dir),
        package_spec,
        *NPM_FETCH_ARGS,
    ]
    last_error: SyncError | None = None
    for attempt in range(1, NPM_INSTALL_MAX_ATTEMPTS + 1):
        _cleanup_stale_npm_package_dirs(prefix_dir, PI_PACKAGE_NAME)
        try:
            _run_command(install_args, timeout=NPM_INSTALL_TIMEOUT_SECONDS)
            return
        except SyncError as exc:
            last_error = exc
            if attempt >= NPM_INSTALL_MAX_ATTEMPTS or not _should_retry_npm_install(exc):
                raise
            time.sleep(min(attempt * 2, 10))
    if last_error is not None:
        raise last_error


def _cleanup_stale_npm_package_dirs(prefix_dir: Path, package_name: str) -> list[str]:
    package_parent, package_leaf = _npm_package_parent_and_leaf(prefix_dir, package_name)
    removed: list[str] = []
    if not package_parent.is_dir():
        return removed
    for stale_path in sorted(package_parent.glob(f".{package_leaf}-*")):
        if stale_path.name == package_leaf:
            continue
        if stale_path.is_dir() and not stale_path.is_symlink():
            shutil.rmtree(stale_path, ignore_errors=True)
            removed.append(stale_path.name)
        elif stale_path.exists() or stale_path.is_symlink():
            stale_path.unlink(missing_ok=True)
            removed.append(stale_path.name)
    return removed


def _npm_package_parent_and_leaf(prefix_dir: Path, package_name: str) -> tuple[Path, str]:
    package_root = prefix_dir / "lib" / "node_modules"
    if package_name.startswith("@") and "/" in package_name:
        scope, name = package_name.split("/", 1)
        return package_root / scope, name
    return package_root, package_name


def _should_retry_npm_install(error: SyncError) -> bool:
    message = str(error).lower()
    retry_markers = (
        "err_socket_timeout",
        "socket timeout",
        "econnreset",
        "etimedout",
        "network",
        "invalid response body",
        "enotempty",
        "directory not empty",
    )
    return any(marker in message for marker in retry_markers)


def _run_command(
    args: list[str],
    *,
    check: bool = True,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    if shutil.which(args[0]) is None:
        raise SyncError(f"Required command not found: {args[0]}")
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=check,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError(f"Command timed out after {timeout:.0f}s ({' '.join(args)})") from exc
