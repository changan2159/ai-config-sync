from __future__ import annotations

import grp
import os
import pwd
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.sync import SyncError


DEFAULT_PI_WEB_HOSTNAME = "0.0.0.0"
DEFAULT_PI_WEB_PORT = 8732
MANAGED_PI_WEB_SERVICE_NAME = "pi-web.service"
PI_WEB_INSTALLER_URL = "https://raw.githubusercontent.com/Epsilondelta-ai/pi-web/main/scripts/install.sh"


@dataclass(frozen=True)
class PiWebPaths:
    target_user: str
    target_group: str
    target_uid: int
    home: Path
    bin_dir: Path
    launcher_path: Path
    service_path: Path
    service_name: str


def default_pi_web_paths(home: Path | None = None) -> PiWebPaths:
    account = _target_account()
    resolved_home = Path(home or account.pw_dir).expanduser().resolve()
    return PiWebPaths(
        target_user=account.pw_name,
        target_group=grp.getgrgid(account.pw_gid).gr_name,
        target_uid=account.pw_uid,
        home=resolved_home,
        bin_dir=resolved_home / ".local" / "bin",
        launcher_path=resolved_home / ".local" / "bin" / "pi-web",
        service_path=Path("/etc/systemd/system") / MANAGED_PI_WEB_SERVICE_NAME,
        service_name=MANAGED_PI_WEB_SERVICE_NAME,
    )


def install_pi_web(home: Path | None = None, version: str | None = None) -> dict[str, Any]:
    paths = default_pi_web_paths(home)
    _require_non_root_runtime_install(paths)
    installer_path = _download_installer_script()
    env = os.environ.copy()
    env["PI_WEB_INSTALL_DIR"] = str(paths.bin_dir)
    env.setdefault("PI_WEB_INSTALL_PI", "auto")
    env.setdefault("PI_WEB_INSTALL_DEFAULT_PLUGINS", "auto")
    if version is not None:
        env["PI_WEB_VERSION"] = _normalize_version_tag(version)
    try:
        _run_command(["sh", str(installer_path)], env=env)
    finally:
        installer_path.unlink(missing_ok=True)

    compat_link = _ensure_pi_cli_compat_symlink(paths.home)
    version_output = _run_command([str(paths.launcher_path), "--version"]).stdout.strip()
    installed_version = _parse_installed_version(version_output)
    expected_version = _normalize_version_tag(version) if version is not None else None
    if expected_version is not None and installed_version != expected_version:
        raise SyncError(
            f"Managed pi-web version check failed: expected '{expected_version}', got '{installed_version or '<empty>'}'"
        )
    return {
        "version": installed_version,
        "version_output": version_output,
        "launcher_path": str(paths.launcher_path),
        "install_dir": str(paths.bin_dir),
        "oauth_compat_link": str(compat_link) if compat_link is not None else None,
    }


def install_pi_web_service(
    home: Path | None = None,
    *,
    port: int = DEFAULT_PI_WEB_PORT,
    hostname: str = DEFAULT_PI_WEB_HOSTNAME,
) -> dict[str, Any]:
    paths = default_pi_web_paths(home)
    _require_root("pi-web-service-install")
    _atomic_write_text(paths.service_path, _build_service_unit(paths, port=port, hostname=hostname))
    return {
        "installed": True,
        "service_name": paths.service_name,
        "service_path": str(paths.service_path),
        "port": port,
        "hostname": hostname,
    }


def start_pi_web_service(
    home: Path | None = None,
    *,
    port: int = DEFAULT_PI_WEB_PORT,
    hostname: str = DEFAULT_PI_WEB_HOSTNAME,
) -> dict[str, Any]:
    paths = default_pi_web_paths(home)
    _require_root("pi-web-service-start")
    _require_managed_runtime(paths)
    install_pi_web_service(home, port=port, hostname=hostname)
    _run_command(["systemctl", "daemon-reload"])
    _run_command(["systemctl", "enable", "--now", paths.service_name])
    status = pi_web_status(home)
    status["port"] = port
    status["hostname"] = hostname
    status["url"] = f"http://127.0.0.1:{port}"
    return status


def stop_pi_web_service(home: Path | None = None) -> dict[str, Any]:
    paths = default_pi_web_paths(home)
    _require_root("pi-web-service-stop")
    _run_command(["systemctl", "disable", "--now", paths.service_name], check=False)
    return pi_web_status(home)


def pi_web_status(home: Path | None = None) -> dict[str, Any]:
    paths = default_pi_web_paths(home)
    version_output: str | None = None
    version: str | None = None
    version_exit_code: int | None = None
    if paths.launcher_path.exists():
        version_proc = _run_command([str(paths.launcher_path), "--version"], check=False)
        version_output = version_proc.stdout.strip() or version_proc.stderr.strip() or None
        version_exit_code = version_proc.returncode
        if version_proc.returncode == 0 and version_output:
            version = _parse_installed_version(version_output)
    active = _run_command(["systemctl", "is-active", paths.service_name], check=False)
    enabled = _run_command(["systemctl", "is-enabled", paths.service_name], check=False)
    return {
        "launcher_path": str(paths.launcher_path),
        "launcher_exists": paths.launcher_path.exists(),
        "version": version,
        "version_output": version_output,
        "version_exit_code": version_exit_code,
        "service_name": paths.service_name,
        "service_path": str(paths.service_path),
        "service_active": active.stdout.strip(),
        "service_active_exit_code": active.returncode,
        "service_enabled": enabled.stdout.strip(),
        "service_enabled_exit_code": enabled.returncode,
    }


def _build_service_unit(paths: PiWebPaths, *, port: int, hostname: str) -> str:
    oauth_index = _resolve_pi_ai_oauth_index(paths.home)
    oauth_env = f"Environment=PI_AI_OAUTH_INDEX={oauth_index}\n" if oauth_index is not None else ""
    return (
        "[Unit]\n"
        "Description=Managed pi-web Server\n"
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
        f"{oauth_env}"
        f"ExecStart={paths.launcher_path} --port {port} --host {hostname}\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def _normalize_version_tag(version: str) -> str:
    cleaned = version.strip()
    if not cleaned:
        raise SyncError("pi-web version must not be empty")
    return cleaned if cleaned.startswith("v") else f"v{cleaned}"


def _parse_installed_version(output: str) -> str:
    cleaned = output.strip()
    if not cleaned.startswith("pi-web "):
        raise SyncError(f"Unexpected pi-web version output: {cleaned or '<empty>'}")
    version = cleaned.split()[-1]
    if not version.startswith("v"):
        raise SyncError(f"Unexpected pi-web version output: {cleaned}")
    return version


def _download_installer_script() -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="pi-web-installer-"))
    script_path = temp_dir / "install.sh"
    try:
        if shutil.which("curl"):
            _run_command(["curl", "-fsSL", "-o", str(script_path), PI_WEB_INSTALLER_URL])
        elif shutil.which("wget"):
            _run_command(["wget", "-qO", str(script_path), PI_WEB_INSTALLER_URL])
        else:
            raise SyncError("Required command not found: curl or wget")
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    return script_path


def _ensure_pi_cli_compat_symlink(home: Path) -> Path | None:
    module_root = _resolve_pi_cli_module_root(home)
    if module_root is None:
        return None
    compat_root = home / ".npm-global" / "lib" / "node_modules" / "@earendil-works"
    compat_root.mkdir(parents=True, exist_ok=True)
    compat_link = compat_root / "pi-coding-agent"
    if compat_link.is_symlink() or compat_link.exists():
        resolved = compat_link.resolve() if compat_link.is_symlink() else compat_link
        if resolved == module_root:
            return compat_link
        if compat_link.is_symlink():
            compat_link.unlink()
        else:
            return compat_link
    compat_link.symlink_to(module_root, target_is_directory=True)
    return compat_link


def _resolve_pi_ai_oauth_index(home: Path) -> Path | None:
    module_root = _resolve_pi_cli_module_root(home)
    if module_root is None:
        return None
    oauth_index = module_root / "node_modules" / "@earendil-works" / "pi-ai" / "dist" / "utils" / "oauth" / "index.js"
    return oauth_index if oauth_index.is_file() else None


def _resolve_pi_cli_module_root(home: Path) -> Path | None:
    pi_path = home / ".local" / "bin" / "pi"
    if not pi_path.exists():
        return None
    resolved = pi_path.resolve()
    candidate = resolved.parent.parent
    package_json = candidate / "package.json"
    return candidate if package_json.is_file() else None


def _target_account() -> pwd.struct_passwd:
    sudo_user = os.environ.get("SUDO_USER")
    if os.geteuid() == 0 and sudo_user and sudo_user != "root":
        return pwd.getpwnam(sudo_user)
    return pwd.getpwuid(os.getuid())


def _require_root(command_name: str) -> None:
    if os.geteuid() != 0:
        raise SyncError(f"{command_name} must run with sudo so it can manage /etc/systemd/system/{MANAGED_PI_WEB_SERVICE_NAME}")


def _require_non_root_runtime_install(paths: PiWebPaths) -> None:
    if os.geteuid() == 0 and paths.target_user != "root":
        raise SyncError(
            "pi-web-install must run as the target login user so the runtime under "
            f"{paths.home} stays user-owned; use sudo only for pi-web-service-* commands"
        )


def _require_managed_runtime(paths: PiWebPaths) -> None:
    if not paths.launcher_path.exists():
        raise SyncError(
            f"pi-web launcher not found at {paths.launcher_path}; run pi-web-install as {paths.target_user} first"
        )


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
    env: dict[str, str] | None = None,
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
            env=env,
        )
    except FileNotFoundError as exc:
        raise SyncError(f"Required command not found: {args[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError(f"Command timed out ({' '.join(args)}): {timeout}s") from exc

    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}"
        raise SyncError(f"Command failed ({' '.join(args)}): {detail}")
    return proc
