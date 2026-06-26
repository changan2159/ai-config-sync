from __future__ import annotations

import json
import os
import pwd
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.errors import SyncError


PI_PACKAGE_NAME = "@earendil-works/pi-coding-agent"
DEFAULT_PI_INSTALL_PREFIX = ".local"


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
    _run_command(
        [
            "npm",
            "install",
            "-g",
            "--ignore-scripts",
            "--prefix",
            str(paths.prefix_dir),
            package_spec,
        ]
    )
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


def _run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if shutil.which(args[0]) is None:
        raise SyncError(f"Required command not found: {args[0]}")
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=check,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "unknown error"
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}") from exc
