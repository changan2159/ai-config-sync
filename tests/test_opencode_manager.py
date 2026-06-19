from __future__ import annotations

from pathlib import Path

import pytest

from ai_config_sync.opencode_manager import (
    DEFAULT_OPENCODE_PORT,
    _activate_release,
    _binary_candidates,
    _build_launcher_script,
    _build_service_unit,
    _require_non_root_runtime_install,
    default_opencode_paths,
)


def test_build_launcher_script_uses_current_and_previous(tmp_path: Path) -> None:
    paths = default_opencode_paths(tmp_path)

    script = _build_launcher_script(paths)

    assert str(paths.state_root) in script
    assert 'for base in "$STATE_ROOT/current" "$STATE_ROOT/previous"' in script
    assert 'check_candidate "$base/opencode"' in script
    assert 'check_candidate "$base/bin/opencode"' in script
    assert 'check_candidate "$base/node_modules/.bin/opencode"' in script
    assert "timeout 20s" in script


def test_build_service_unit_uses_managed_wrapper(tmp_path: Path) -> None:
    paths = default_opencode_paths(tmp_path)

    unit = _build_service_unit(paths, port=DEFAULT_OPENCODE_PORT, hostname="127.0.0.1")

    assert "Description=Managed OpenCode Web Server" in unit
    assert f"User={paths.target_user}" in unit
    assert f"Group={paths.target_group}" in unit
    assert f"ExecStart={paths.launcher_path} serve --port 3000 --hostname 127.0.0.1" in unit
    assert f"WorkingDirectory={paths.home}" in unit
    assert "WantedBy=multi-user.target" in unit


def test_activate_release_preserves_previous_target(tmp_path: Path) -> None:
    paths = default_opencode_paths(tmp_path)
    old_release = paths.releases_dir / "1.17.7"
    new_release = paths.releases_dir / "1.17.8"
    old_release.mkdir(parents=True)
    new_release.mkdir(parents=True)
    paths.current_link.parent.mkdir(parents=True, exist_ok=True)
    paths.current_link.symlink_to(old_release, target_is_directory=True)

    _activate_release(paths, new_release)

    assert paths.current_link.resolve() == new_release
    assert paths.previous_link.resolve() == old_release


def test_binary_candidates_include_binary_and_legacy_paths(tmp_path: Path) -> None:
    candidates = _binary_candidates(tmp_path)

    assert candidates == [
        tmp_path / "opencode",
        tmp_path / "bin" / "opencode",
        tmp_path / "node_modules" / ".bin" / "opencode",
    ]


def test_require_non_root_runtime_install_rejects_sudo_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ai_config_sync.opencode_manager.os.geteuid", lambda: 0)

    paths = default_opencode_paths(tmp_path)

    with pytest.raises(RuntimeError, match="opencode-install must run as the target login user"):
        _require_non_root_runtime_install(paths)
