from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_config_sync.errors import SyncError
from ai_config_sync.pi_manager import (
    PiPaths,
    _require_non_root_runtime_install,
    default_pi_paths,
    install_pi,
    pi_status,
)


def test_require_non_root_runtime_install_rejects_sudo_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_config_sync.pi_manager.os.geteuid", lambda: 0)

    paths = default_pi_paths(tmp_path)

    with pytest.raises(SyncError, match="pi-install must run as the target login user"):
        _require_non_root_runtime_install(paths)


def test_require_non_root_runtime_install_allows_root_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_config_sync.pi_manager.os.geteuid", lambda: 0)

    paths = PiPaths(
        target_user="root",
        target_uid=0,
        home=tmp_path,
        prefix_dir=tmp_path / ".local",
        bin_dir=tmp_path / ".local" / "bin",
        launcher_path=tmp_path / ".local" / "bin" / "pi",
    )

    _require_non_root_runtime_install(paths)


def test_install_pi_runs_global_npm_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = default_pi_paths(tmp_path)
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        assert check is True
        calls.append(args)
        if args[:3] == ["npm", "install", "-g"]:
            paths.bin_dir.mkdir(parents=True, exist_ok=True)
            paths.launcher_path.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args == [str(paths.launcher_path), "--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="pi 0.73.0\n", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("ai_config_sync.pi_manager._run_command", fake_run_command)

    result = install_pi(home=tmp_path, version="0.73.0")

    assert calls == [
        [
            "npm",
            "install",
            "-g",
            "--ignore-scripts",
            "--prefix",
            str(paths.prefix_dir),
            "@earendil-works/pi-coding-agent@0.73.0",
        ],
        [str(paths.launcher_path), "--version"],
    ]
    assert result["version"] == "0.73.0"
    assert result["launcher_path"] == str(paths.launcher_path)
    assert result["install_prefix"] == str(paths.prefix_dir)


def test_pi_status_reports_launcher_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = default_pi_paths(tmp_path)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    paths.launcher_path.write_text("", encoding="utf-8")

    def fake_run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        assert args == [str(paths.launcher_path), "--version"]
        assert check is False
        return subprocess.CompletedProcess(args, 0, stdout="pi 0.73.0\n", stderr="")

    monkeypatch.setattr("ai_config_sync.pi_manager._run_command", fake_run_command)

    result = pi_status(home=tmp_path)

    assert result["launcher_exists"] is True
    assert result["version"] == "0.73.0"
    assert result["version_output"] == "pi 0.73.0"
