from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_config_sync.errors import SyncError
from ai_config_sync.pi_manager import (
    PiPaths,
    _cleanup_stale_npm_package_dirs,
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

    def fake_run_command(
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert check is True
        if args[:3] == ["npm", "install", "-g"]:
            assert timeout == 300
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
            "--fetch-retries",
            "5",
            "--fetch-retry-mintimeout",
            "2000",
            "--fetch-retry-maxtimeout",
            "30000",
            "--fetch-timeout",
            "300000",
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

    def fake_run_command(
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert args == [str(paths.launcher_path), "--version"]
        assert check is False
        assert timeout is None
        return subprocess.CompletedProcess(args, 0, stdout="pi 0.73.0\n", stderr="")

    monkeypatch.setattr("ai_config_sync.pi_manager._run_command", fake_run_command)

    result = pi_status(home=tmp_path)

    assert result["launcher_exists"] is True
    assert result["version"] == "0.73.0"
    assert result["version_output"] == "pi 0.73.0"


def test_pi_status_accepts_plain_semver_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = default_pi_paths(tmp_path)
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    paths.launcher_path.write_text("", encoding="utf-8")

    def fake_run_command(
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        assert args == [str(paths.launcher_path), "--version"]
        assert check is False
        assert timeout is None
        return subprocess.CompletedProcess(args, 0, stdout="0.80.2\n", stderr="")

    monkeypatch.setattr("ai_config_sync.pi_manager._run_command", fake_run_command)

    result = pi_status(home=tmp_path)

    assert result["launcher_exists"] is True
    assert result["version"] == "0.80.2"
    assert result["version_output"] == "0.80.2"


def test_cleanup_stale_npm_package_dirs_removes_hidden_temp_dirs(tmp_path: Path) -> None:
    scope_dir = tmp_path / ".local" / "lib" / "node_modules" / "@earendil-works"
    scope_dir.mkdir(parents=True)
    stale_dir = scope_dir / ".pi-coding-agent-abcd1234"
    stale_dir.mkdir()
    package_dir = scope_dir / "pi-coding-agent"
    package_dir.mkdir()

    removed = _cleanup_stale_npm_package_dirs(tmp_path / ".local", "@earendil-works/pi-coding-agent")

    assert removed == [".pi-coding-agent-abcd1234"]
    assert not stale_dir.exists()
    assert package_dir.exists()


def test_install_pi_retries_retryable_npm_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paths = default_pi_paths(tmp_path)
    stale_dir = paths.prefix_dir / "lib" / "node_modules" / "@earendil-works" / ".pi-coding-agent-stale"
    stale_dir.mkdir(parents=True)
    calls: list[list[str]] = []
    attempt = {"count": 0}

    def fake_run_command(
        args: list[str],
        *,
        check: bool = True,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[:3] == ["npm", "install", "-g"]:
            attempt["count"] += 1
            if attempt["count"] == 1:
                raise SyncError("Command failed (npm install): npm ERR! code ERR_SOCKET_TIMEOUT")
            paths.bin_dir.mkdir(parents=True, exist_ok=True)
            paths.launcher_path.write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args == [str(paths.launcher_path), "--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="pi 0.80.3\n", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("ai_config_sync.pi_manager._run_command", fake_run_command)
    monkeypatch.setattr("ai_config_sync.pi_manager.time.sleep", lambda _: None)

    result = install_pi(home=tmp_path, version="0.80.3")

    assert attempt["count"] == 2
    assert not stale_dir.exists()
    assert result["version"] == "0.80.3"
