from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import ai_config_sync.pi_package_manager as pi_package_manager


def test_sync_pi_packages_installs_missing_managed_packages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "pi-mcp-adapter": "^2.10.0",
                    "manual-package": "^1.0.0",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    installed_mcp = package_dir / "node_modules" / "pi-mcp-adapter"
    installed_mcp.mkdir(parents=True, exist_ok=True)
    (installed_mcp / "package.json").write_text('{"name":"pi-mcp-adapter"}\n', encoding="utf-8")
    installed_manual = package_dir / "node_modules" / "manual-package"
    installed_manual.mkdir(parents=True, exist_ok=True)
    (installed_manual / "package.json").write_text('{"name":"manual-package"}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        data = json.loads(package_json.read_text(encoding="utf-8"))
        data["dependencies"]["pi-subagents"] = "^0.30.0"
        package_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        installed_subagents = package_dir / "node_modules" / "pi-subagents"
        installed_subagents.mkdir(parents=True, exist_ok=True)
        (installed_subagents / "package.json").write_text('{"name":"pi-subagents"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.sync_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-mcp-adapter", "npm:pi-subagents"),
        previous_packages=["npm:pi-mcp-adapter"],
    )

    assert calls == [["npm", "install", "--no-fund", "--no-audit", "pi-subagents"]]
    assert result == {
        "installed": ["npm:pi-subagents"],
        "removed": [],
        "installed_package_names": ["manual-package", "pi-mcp-adapter", "pi-subagents"],
    }


def test_sync_pi_packages_reinstalls_when_dependency_exists_but_node_modules_package_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "pi-subagents": "^0.30.0",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        installed_package = package_dir / "node_modules" / "pi-subagents"
        installed_package.mkdir(parents=True, exist_ok=True)
        (installed_package / "package.json").write_text('{"name":"pi-subagents"}\n', encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.sync_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-subagents",),
        previous_packages=["npm:pi-subagents"],
    )

    assert calls == [["npm", "install", "--no-fund", "--no-audit", "pi-subagents"]]
    assert result == {
        "installed": ["npm:pi-subagents"],
        "removed": [],
        "installed_package_names": ["pi-subagents"],
    }


def test_sync_pi_packages_removes_stale_managed_packages_without_touching_manual_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "manual-package": "^1.0.0",
                    "pi-subagents": "^0.30.0",
                    "pi-nano-context": "^0.1.1",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    installed_manual = package_dir / "node_modules" / "manual-package"
    installed_manual.mkdir(parents=True, exist_ok=True)
    (installed_manual / "package.json").write_text('{"name":"manual-package"}\n', encoding="utf-8")
    installed_subagents = package_dir / "node_modules" / "pi-subagents"
    installed_subagents.mkdir(parents=True, exist_ok=True)
    (installed_subagents / "package.json").write_text('{"name":"pi-subagents"}\n', encoding="utf-8")
    installed_nano = package_dir / "node_modules" / "pi-nano-context"
    installed_nano.mkdir(parents=True, exist_ok=True)
    (installed_nano / "package.json").write_text('{"name":"pi-nano-context"}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        data = json.loads(package_json.read_text(encoding="utf-8"))
        data["dependencies"].pop("pi-nano-context", None)
        package_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        nano_dir = package_dir / "node_modules" / "pi-nano-context"
        if nano_dir.exists():
            for child in nano_dir.iterdir():
                child.unlink()
            nano_dir.rmdir()
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.sync_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-subagents",),
        previous_packages=["npm:pi-subagents", "npm:pi-nano-context"],
    )

    assert calls == [["npm", "uninstall", "--no-fund", "--no-audit", "pi-nano-context"]]
    assert result == {
        "installed": [],
        "removed": ["npm:pi-nano-context"],
        "installed_package_names": ["manual-package", "pi-subagents"],
    }


def test_sync_pi_packages_uninstalls_stale_managed_dependency_even_when_node_modules_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "manual-package": "^1.0.0",
                    "pi-nano-context": "^0.1.1",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    installed_manual = package_dir / "node_modules" / "manual-package"
    installed_manual.mkdir(parents=True, exist_ok=True)
    (installed_manual / "package.json").write_text('{"name":"manual-package"}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        data = json.loads(package_json.read_text(encoding="utf-8"))
        data["dependencies"].pop("pi-nano-context", None)
        package_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.sync_pi_packages(
        settings_path=settings_path,
        packages=(),
        previous_packages=["npm:pi-nano-context"],
    )

    assert calls == [["npm", "uninstall", "--no-fund", "--no-audit", "pi-nano-context"]]
    assert result == {
        "installed": [],
        "removed": ["npm:pi-nano-context"],
        "installed_package_names": ["manual-package"],
    }


def test_inspect_pi_packages_reports_managed_versions(tmp_path: Path) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "pi-subagents": "^0.30.0",
                    "manual-package": "^1.0.0",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    installed_subagents = package_dir / "node_modules" / "pi-subagents"
    installed_subagents.mkdir(parents=True, exist_ok=True)
    (installed_subagents / "package.json").write_text('{"name":"pi-subagents","version":"0.31.2"}\n', encoding="utf-8")

    result = pi_package_manager.inspect_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-subagents", "npm:pi-goal"),
        latest_version_resolver=lambda name: {"pi-subagents": "0.32.0", "pi-goal": "0.2.0"}.get(name),
    )

    assert result["managed_entries"] == [
        {
            "spec": "npm:pi-subagents",
            "name": "pi-subagents",
            "declared_version": "^0.30.0",
            "installed_version": "0.31.2",
            "latest_version": "0.32.0",
            "has_update": True,
            "installed": True,
        },
        {
            "spec": "npm:pi-goal",
            "name": "pi-goal",
            "declared_version": None,
            "installed_version": None,
            "latest_version": "0.2.0",
            "has_update": False,
            "installed": False,
        },
    ]


def test_upgrade_pi_packages_reinstalls_all_managed_specs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text('{"name":"pi-extensions","private":true,"dependencies":{}}\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        for package_name in ("pi-subagents", "pi-goal"):
            package_path = package_dir / "node_modules" / package_name
            package_path.mkdir(parents=True, exist_ok=True)
            (package_path / "package.json").write_text(
                json.dumps({"name": package_name, "version": "1.0.0"}) + "\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.upgrade_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-subagents", "npm:pi-goal"),
    )

    assert calls == [["npm", "install", "--no-fund", "--no-audit", "pi-subagents", "pi-goal"]]
    assert result["upgraded"] == ["npm:pi-subagents", "npm:pi-goal"]


def test_upgrade_pi_packages_supports_single_target_spec(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings_path = tmp_path / "pi" / "settings.json"
    package_dir = settings_path.parent / "npm"
    package_json = package_dir / "package.json"
    package_dir.mkdir(parents=True)
    package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {
                    "pi-subagents": "^0.31.0",
                    "pi-goal": "^0.1.7",
                },
            }
        ) + "\n",
        encoding="utf-8",
    )
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        assert cwd == package_dir
        calls.append(args)
        for package_name, version in (("pi-subagents", "1.1.0"), ("pi-goal", "0.1.7")):
            package_path = package_dir / "node_modules" / package_name
            package_path.mkdir(parents=True, exist_ok=True)
            (package_path / "package.json").write_text(
                json.dumps({"name": package_name, "version": version}) + "\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(pi_package_manager, "_run_command", fake_run_command)

    result = pi_package_manager.upgrade_pi_packages(
        settings_path=settings_path,
        packages=("npm:pi-subagents", "npm:pi-goal"),
        target_specs=("npm:pi-subagents",),
    )

    assert calls == [["npm", "install", "--no-fund", "--no-audit", "pi-subagents"]]
    assert result["upgraded"] == ["npm:pi-subagents"]
