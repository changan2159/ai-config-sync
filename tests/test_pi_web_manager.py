from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_config_sync.pi_web_manager import (
    DEFAULT_PI_WEB_PORT,
    _build_service_unit,
    _require_non_root_runtime_install,
    _resolve_pi_ai_oauth_index,
    default_pi_web_paths,
    install_pi_web,
)


def test_build_service_unit_uses_managed_binary(tmp_path: Path) -> None:
    paths = default_pi_web_paths(tmp_path)
    module_root = tmp_path / ".local" / "lib" / "node_modules" / "@earendil-works" / "pi-coding-agent"
    oauth_index = module_root / "node_modules" / "@earendil-works" / "pi-ai" / "dist" / "utils" / "oauth" / "index.js"
    oauth_index.parent.mkdir(parents=True, exist_ok=True)
    oauth_index.write_text("", encoding="utf-8")
    package_json = module_root / "package.json"
    package_json.parent.mkdir(parents=True, exist_ok=True)
    package_json.write_text("{}\n", encoding="utf-8")
    cli_entry = module_root / "dist" / "cli.js"
    cli_entry.parent.mkdir(parents=True, exist_ok=True)
    cli_entry.write_text("", encoding="utf-8")
    paths.launcher_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".local" / "bin" / "pi").symlink_to(cli_entry)
    paths.launcher_path.symlink_to(cli_entry)

    unit = _build_service_unit(paths, port=DEFAULT_PI_WEB_PORT, hostname="127.0.0.1")

    assert "Description=Managed pi-web Server" in unit
    assert f"User={paths.target_user}" in unit
    assert f"Group={paths.target_group}" in unit
    assert f"Environment=PI_AI_OAUTH_INDEX={oauth_index}" in unit
    assert f"ExecStart={paths.launcher_path} --port 8732 --host 127.0.0.1" in unit
    assert f"WorkingDirectory={paths.home}" in unit
    assert "WantedBy=multi-user.target" in unit


def test_require_non_root_runtime_install_rejects_sudo_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_config_sync.pi_web_manager.os.geteuid", lambda: 0)

    paths = default_pi_web_paths(tmp_path)

    with pytest.raises(RuntimeError, match="pi-web-install must run as the target login user"):
        _require_non_root_runtime_install(paths)


def test_install_pi_web_runs_official_installer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = default_pi_web_paths(tmp_path)
    installer_path = tmp_path / "install.sh"
    installer_path.write_text("#!/usr/bin/env sh\n", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, str] | None]] = []
    module_root = tmp_path / ".local" / "lib" / "node_modules" / "@earendil-works" / "pi-coding-agent"
    oauth_index = module_root / "node_modules" / "@earendil-works" / "pi-ai" / "dist" / "utils" / "oauth" / "index.js"
    cli_entry = module_root / "dist" / "cli.js"

    def fake_run_command(
        args: list[str],
        *,
        cwd: Path | None = None,
        timeout: int | None = None,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, timeout, check
        calls.append((args, env))
        if args == ["sh", str(installer_path)]:
            paths.bin_dir.mkdir(parents=True, exist_ok=True)
            oauth_index.parent.mkdir(parents=True, exist_ok=True)
            oauth_index.write_text("", encoding="utf-8")
            (module_root / "package.json").write_text("{}\n", encoding="utf-8")
            cli_entry.parent.mkdir(parents=True, exist_ok=True)
            cli_entry.write_text("", encoding="utf-8")
            (tmp_path / ".local" / "bin" / "pi").symlink_to(cli_entry)
            paths.launcher_path.symlink_to(cli_entry)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args == [str(paths.launcher_path), "--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="pi-web v1.2.3\n", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("ai_config_sync.pi_web_manager._download_installer_script", lambda: installer_path)
    monkeypatch.setattr("ai_config_sync.pi_web_manager._run_command", fake_run_command)

    result = install_pi_web(home=tmp_path, version="1.2.3")

    assert calls[0][0] == ["sh", str(installer_path)]
    assert calls[0][1] is not None
    assert calls[0][1]["PI_WEB_VERSION"] == "v1.2.3"
    assert calls[0][1]["PI_WEB_INSTALL_DIR"] == str(paths.bin_dir)
    assert result["version"] == "v1.2.3"
    assert result["launcher_path"] == str(paths.launcher_path)
    assert result["oauth_compat_link"] == str(tmp_path / ".npm-global" / "lib" / "node_modules" / "@earendil-works" / "pi-coding-agent")
    assert _resolve_pi_ai_oauth_index(tmp_path) == oauth_index
