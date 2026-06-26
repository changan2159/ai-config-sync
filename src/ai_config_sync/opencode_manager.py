from __future__ import annotations

import json
import os
import platform
import pwd
import grp
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.sync import SyncError


DEFAULT_OPENCODE_HOSTNAME = "0.0.0.0"
DEFAULT_OPENCODE_PORT = 3000
DEFAULT_OPENCODE_HEALTH_TIMEOUT_SEC = 20
MANAGED_OPENCODE_SERVICE_NAME = "opencode-web.service"
LEGACY_OPENCODE_USER_SERVICE_NAME = "opencode-web-managed.service"
OPENCODE_RELEASE_REPO = "https://github.com/anomalyco/opencode/releases/download"
OPENCODE_RELEASES_API = "https://api.github.com/repos/anomalyco/opencode/releases/latest"
OPENCODE_RELEASES_LATEST_PAGE = "https://github.com/anomalyco/opencode/releases/latest"


@dataclass(frozen=True)
class OpencodePaths:
    target_user: str
    target_group: str
    target_uid: int
    home: Path
    state_root: Path
    releases_dir: Path
    stage_dir: Path
    current_link: Path
    previous_link: Path
    metadata_path: Path
    bin_dir: Path
    launcher_path: Path
    service_path: Path
    service_name: str
    legacy_user_service_path: Path
    legacy_user_service_name: str


def default_opencode_paths(home: Path | None = None) -> OpencodePaths:
    account = _target_account()
    resolved_home = Path(home or account.pw_dir).expanduser().resolve()
    state_root = resolved_home / ".local" / "share" / "ai-config-sync" / "opencode"
    return OpencodePaths(
        target_user=account.pw_name,
        target_group=grp.getgrgid(account.pw_gid).gr_name,
        target_uid=account.pw_uid,
        home=resolved_home,
        state_root=state_root,
        releases_dir=state_root / "releases",
        stage_dir=state_root / ".stage",
        current_link=state_root / "current",
        previous_link=state_root / "previous",
        metadata_path=state_root / "state.json",
        bin_dir=resolved_home / ".local" / "bin",
        launcher_path=resolved_home / ".local" / "bin" / "opencode",
        service_path=Path("/etc/systemd/system") / MANAGED_OPENCODE_SERVICE_NAME,
        service_name=MANAGED_OPENCODE_SERVICE_NAME,
        legacy_user_service_path=resolved_home / ".config" / "systemd" / "user" / LEGACY_OPENCODE_USER_SERVICE_NAME,
        legacy_user_service_name=LEGACY_OPENCODE_USER_SERVICE_NAME,
    )


def install_opencode(home: Path | None = None, version: str | None = None) -> dict[str, Any]:
    paths = default_opencode_paths(home)
    _require_non_root_runtime_install(paths)
    resolved_version = version or _latest_opencode_version()
    _ensure_opencode_dirs(paths)

    release_dir = paths.releases_dir / resolved_version
    installed = False
    release_target = _release_target()
    if not _is_healthy_release(release_dir, expected_version=resolved_version):
        stage_dir = _download_release_to_stage(paths, resolved_version, release_target)
        _validate_release(stage_dir, expected_version=resolved_version)
        _commit_release(stage_dir, release_dir)
        installed = True

    _activate_release(paths, release_dir)
    _write_launcher(paths)
    _write_metadata(paths, resolved_version, release_target)

    return {
        "version": resolved_version,
        "installed": installed,
        "release_target": release_target,
        "release_dir": str(release_dir),
        "launcher_path": str(paths.launcher_path),
        "current_target": str(paths.current_link.resolve()),
        "previous_target": str(paths.previous_link.resolve()) if paths.previous_link.is_symlink() else None,
    }


def install_opencode_service(
    home: Path | None = None,
    *,
    port: int = DEFAULT_OPENCODE_PORT,
    hostname: str = DEFAULT_OPENCODE_HOSTNAME,
) -> dict[str, Any]:
    paths = default_opencode_paths(home)
    _require_root("opencode-service-install")
    _atomic_write_text(paths.service_path, _build_service_unit(paths, port=port, hostname=hostname))
    return {
        "installed": True,
        "service_name": paths.service_name,
        "service_path": str(paths.service_path),
        "port": port,
        "hostname": hostname,
    }


def start_opencode_service(
    home: Path | None = None,
    *,
    port: int = DEFAULT_OPENCODE_PORT,
    hostname: str = DEFAULT_OPENCODE_HOSTNAME,
) -> dict[str, Any]:
    paths = default_opencode_paths(home)
    _require_root("opencode-service-start")
    _require_managed_runtime(paths)
    install_opencode_service(home, port=port, hostname=hostname)
    _disable_legacy_user_service(paths)
    _run_command(["systemctl", "daemon-reload"])
    _run_command(["systemctl", "enable", "--now", paths.service_name])
    return opencode_status(home)


def stop_opencode_service(home: Path | None = None) -> dict[str, Any]:
    paths = default_opencode_paths(home)
    _require_root("opencode-service-stop")
    _run_command(["systemctl", "disable", "--now", paths.service_name], check=False)
    return opencode_status(home)


def opencode_status(home: Path | None = None) -> dict[str, Any]:
    paths = default_opencode_paths(home)
    current_target = str(paths.current_link.resolve()) if paths.current_link.is_symlink() else None
    previous_target = str(paths.previous_link.resolve()) if paths.previous_link.is_symlink() else None
    current_version = Path(current_target).name if current_target else None
    previous_version = Path(previous_target).name if previous_target else None
    active = _run_command(["systemctl", "is-active", paths.service_name], check=False)
    enabled = _run_command(["systemctl", "is-enabled", paths.service_name], check=False)
    legacy_active = _run_user_systemctl(paths, ["is-active", paths.legacy_user_service_name], check=False)
    legacy_enabled = _run_user_systemctl(paths, ["is-enabled", paths.legacy_user_service_name], check=False)
    return {
        "launcher_path": str(paths.launcher_path),
        "launcher_exists": paths.launcher_path.exists(),
        "current_version": current_version,
        "current_target": current_target,
        "previous_version": previous_version,
        "previous_target": previous_target,
        "service_name": paths.service_name,
        "service_path": str(paths.service_path),
        "service_active": active.stdout.strip(),
        "service_active_exit_code": active.returncode,
        "service_enabled": enabled.stdout.strip(),
        "service_enabled_exit_code": enabled.returncode,
        "legacy_user_service_name": paths.legacy_user_service_name,
        "legacy_user_service_path": str(paths.legacy_user_service_path),
        "legacy_user_service_exists": paths.legacy_user_service_path.exists(),
        "legacy_user_service_active": legacy_active.stdout.strip(),
        "legacy_user_service_active_exit_code": legacy_active.returncode,
        "legacy_user_service_enabled": legacy_enabled.stdout.strip(),
        "legacy_user_service_enabled_exit_code": legacy_enabled.returncode,
        "metadata_path": str(paths.metadata_path),
    }


def _ensure_opencode_dirs(paths: OpencodePaths) -> None:
    paths.releases_dir.mkdir(parents=True, exist_ok=True)
    paths.stage_dir.mkdir(parents=True, exist_ok=True)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)


def _download_release_to_stage(paths: OpencodePaths, version: str, target: str) -> Path:
    stage_dir = Path(tempfile.mkdtemp(prefix=f"opencode-{version}-", dir=paths.stage_dir))
    archive_ext = ".zip" if platform.system().lower().startswith("win") else ".tar.gz"
    archive_name = f"opencode-{target}{archive_ext}"
    archive_path = stage_dir / archive_name
    url = f"{OPENCODE_RELEASE_REPO}/v{version}/{archive_name}"
    try:
        _run_command(["curl", "-fsSL", "--retry", "3", "--location", "-o", str(archive_path), url])
        _extract_archive(archive_path, stage_dir)
        archive_path.unlink(missing_ok=True)
        binary_path = _preferred_binary_path(stage_dir)
        if not binary_path.is_file():
            raise SyncError(f"Managed OpenCode archive did not produce a runnable binary for target '{target}'")
        binary_path.chmod(0o755)
        return stage_dir
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def _extract_archive(archive_path: Path, stage_dir: Path) -> None:
    if archive_path.suffix == ".zip":
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(stage_dir)
        return
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(stage_dir)


def _commit_release(stage_dir: Path, release_dir: Path) -> None:
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.parent.mkdir(parents=True, exist_ok=True)
    stage_dir.replace(release_dir)


def _validate_release(stage_dir: Path, *, expected_version: str) -> None:
    binary = _preferred_binary_path(stage_dir)
    if not binary.is_file():
        raise SyncError(f"Managed OpenCode install did not produce {binary}")

    version_proc = _run_command([str(binary), "--version"], timeout=DEFAULT_OPENCODE_HEALTH_TIMEOUT_SEC)
    actual_version = version_proc.stdout.strip()
    if actual_version != expected_version:
        raise SyncError(
            f"Managed OpenCode version check failed: expected '{expected_version}', got '{actual_version or '<empty>'}'"
        )

    port = _reserve_tcp_port()
    serve_proc = subprocess.Popen(
        [str(binary), "serve", "--port", str(port), "--hostname", "127.0.0.1"],
        cwd=stage_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    started = False
    try:
        deadline = time.time() + DEFAULT_OPENCODE_HEALTH_TIMEOUT_SEC
        while time.time() < deadline:
            if serve_proc.poll() is not None:
                break
            if _can_connect("127.0.0.1", port):
                started = True
                break
            time.sleep(0.2)
        if not started:
            stdout, stderr = serve_proc.communicate(timeout=2)
            detail = stderr.strip() or stdout.strip() or "health check timed out"
            raise SyncError(f"Managed OpenCode serve health check failed: {detail}")
    finally:
        if serve_proc.poll() is None:
            serve_proc.terminate()
            try:
                serve_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                serve_proc.kill()
                serve_proc.wait(timeout=5)


def _is_healthy_release(release_dir: Path, *, expected_version: str) -> bool:
    binary = _managed_binary_path(release_dir)
    if not binary.is_file():
        return False
    proc = _run_command([str(binary), "--version"], timeout=DEFAULT_OPENCODE_HEALTH_TIMEOUT_SEC, check=False)
    return proc.returncode == 0 and proc.stdout.strip() == expected_version


def _activate_release(paths: OpencodePaths, release_dir: Path) -> None:
    current_target = paths.current_link.resolve() if paths.current_link.is_symlink() else None
    if current_target and current_target.exists() and current_target != release_dir:
        _replace_symlink(paths.previous_link, current_target)
    _replace_symlink(paths.current_link, release_dir)


def _replace_symlink(link_path: Path, target: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    temp_link = link_path.with_name(f".{link_path.name}.tmp")
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    temp_link.symlink_to(target, target_is_directory=True)
    temp_link.replace(link_path)


def _write_launcher(paths: OpencodePaths) -> None:
    _atomic_write_text(paths.launcher_path, _build_launcher_script(paths), mode=0o755)


def _write_metadata(paths: OpencodePaths, version: str, release_target: str) -> None:
    payload = {
        "updated_at": int(time.time()),
        "version": version,
        "release_target": release_target,
        "current_target": str(paths.current_link.resolve()),
        "previous_target": str(paths.previous_link.resolve()) if paths.previous_link.is_symlink() else None,
    }
    _atomic_write_text(paths.metadata_path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _build_launcher_script(paths: OpencodePaths) -> str:
    return f"""#!/bin/bash
set -euo pipefail

STATE_ROOT="{paths.state_root}"

check_candidate() {{
  local candidate="$1"
  if [[ -x "$candidate" ]] && timeout {DEFAULT_OPENCODE_HEALTH_TIMEOUT_SEC}s "$candidate" --version >/dev/null 2>&1; then
    printf '%s\\n' "$candidate"
    return 0
  fi
  return 1
}}

pick_release() {{
  local base
  for base in "$STATE_ROOT/current" "$STATE_ROOT/previous"; do
    [[ -e "$base" ]] || continue
    check_candidate "$base/opencode" && return 0
    check_candidate "$base/bin/opencode" && return 0
    check_candidate "$base/node_modules/.bin/opencode" && return 0
  done
  echo "No healthy managed opencode release found under $STATE_ROOT" >&2
  exit 1
}}

binary="$(pick_release)"
exec "$binary" "$@"
"""


def _build_service_unit(paths: OpencodePaths, *, port: int, hostname: str) -> str:
    return (
        "[Unit]\n"
        "Description=Managed OpenCode Web Server\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"User={paths.target_user}\n"
        f"Group={paths.target_group}\n"
        f"WorkingDirectory={paths.home}\n"
        f"Environment=HOME={paths.home}\n"
        f"Environment=USER={paths.target_user}\n"
        f"Environment=LOGNAME={paths.target_user}\n"
        f"Environment=PATH={paths.home / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin\n"
        "Environment=NODE_ENV=production\n"
        f"ExecStart={paths.launcher_path} serve --port {port} --hostname {hostname}\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def _preferred_binary_path(release_dir: Path) -> Path:
    for candidate in _binary_candidates(release_dir):
        if candidate.is_file():
            return candidate
    return release_dir / "opencode"


def _managed_binary_path(release_dir: Path) -> Path:
    for candidate in _managed_binary_candidates(release_dir):
        if candidate.is_file():
            return candidate
    return release_dir / "opencode"


def _binary_candidates(release_dir: Path) -> list[Path]:
    return [
        *_managed_binary_candidates(release_dir),
        release_dir / "node_modules" / ".bin" / "opencode",
    ]


def _managed_binary_candidates(release_dir: Path) -> list[Path]:
    return [
        release_dir / "opencode",
        release_dir / "bin" / "opencode",
    ]


def _latest_opencode_version() -> str:
    proc = _run_command(
        [
            "curl",
            "-fsSL",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            "X-GitHub-Api-Version: 2022-11-28",
            OPENCODE_RELEASES_API,
        ],
        check=False,
    )
    if proc.returncode == 0:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise SyncError("Unable to parse the latest OpenCode release metadata from GitHub") from exc
        version = str(payload.get("tag_name", "")).strip().removeprefix("v")
        if version:
            return version

    fallback = _run_command(
        ["curl", "-fsSI", OPENCODE_RELEASES_LATEST_PAGE],
        check=False,
    )
    if fallback.returncode == 0:
        location_match = next(
            (
                line.split(":", 1)[1].strip()
                for line in fallback.stdout.splitlines()
                if line.lower().startswith("location:")
            ),
            None,
        )
        if location_match:
            version = Path(location_match).name.strip().removeprefix("v")
            if version:
                return version

    raise SyncError("Unable to resolve the latest OpenCode release version from GitHub")


def _release_target() -> str:
    system_name = platform.system().lower()
    machine = platform.machine().lower()

    if system_name == "linux":
        os_name = "linux"
    elif system_name == "darwin":
        os_name = "darwin"
    elif system_name == "windows":
        os_name = "windows"
    else:
        raise SyncError(f"Unsupported OpenCode host OS: {platform.system()}")

    if machine in {"x86_64", "amd64"}:
        arch = "x64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise SyncError(f"Unsupported OpenCode host architecture: {platform.machine()}")

    target = f"{os_name}-{arch}"
    if os_name == "linux" and arch == "x64" and not _linux_x64_has_avx2():
        target = f"{target}-baseline"
    if os_name == "linux" and _linux_is_musl():
        target = f"{target}-musl"
    return target


def _linux_x64_has_avx2() -> bool:
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.exists():
        return False
    return " avx2 " in f" {cpuinfo.read_text(encoding='utf-8', errors='ignore').lower()} "


def _linux_is_musl() -> bool:
    if Path("/etc/alpine-release").exists():
        return True
    proc = _run_command(["ldd", "--version"], check=False)
    combined = f"{proc.stdout}\n{proc.stderr}".lower()
    return "musl" in combined


def _reserve_tcp_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _can_connect(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
        except OSError:
            return False
    return True


def _target_account() -> pwd.struct_passwd:
    sudo_user = os.environ.get("SUDO_USER")
    if os.geteuid() == 0 and sudo_user and sudo_user != "root":
        return pwd.getpwnam(sudo_user)
    return pwd.getpwuid(os.getuid())


def _require_root(command_name: str) -> None:
    if os.geteuid() != 0:
        raise SyncError(f"{command_name} must run with sudo so it can manage /etc/systemd/system/{MANAGED_OPENCODE_SERVICE_NAME}")


def _require_non_root_runtime_install(paths: OpencodePaths) -> None:
    if os.geteuid() == 0 and paths.target_user != "root":
        raise SyncError(
            "opencode-install must run as the target login user so the managed runtime under "
            f"{paths.home} stays user-owned; use sudo only for opencode-service-* commands"
        )


def _require_managed_runtime(paths: OpencodePaths) -> None:
    if not paths.launcher_path.exists():
        raise SyncError(
            f"Managed OpenCode launcher not found at {paths.launcher_path}; run opencode-install as {paths.target_user} first"
        )


def _run_user_systemctl(paths: OpencodePaths, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    if os.geteuid() == 0 and paths.target_user != "root":
        return _run_command(
            [
                "sudo",
                "-u",
                paths.target_user,
                "env",
                f"XDG_RUNTIME_DIR=/run/user/{paths.target_uid}",
                "systemctl",
                "--user",
                *args,
            ],
            check=check,
        )
    return _run_command(["systemctl", "--user", *args], check=check)


def _disable_legacy_user_service(paths: OpencodePaths) -> None:
    if not paths.legacy_user_service_path.exists():
        return
    _run_user_systemctl(paths, ["disable", "--now", paths.legacy_user_service_name], check=False)


def _atomic_write_text(path: Path, content: str, *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    if mode is not None:
        temp_path.chmod(mode)
    temp_path.replace(path)


def _run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"Required command not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError(f"Command timed out ({' '.join(args)}): {timeout}s") from exc

    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}")
    return proc
