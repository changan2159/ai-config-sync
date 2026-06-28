from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_config_sync import web_server


def test_all_tool_scripts_exist() -> None:
    for meta in web_server.TOOLS.values():
        assert (web_server.REPO_ROOT / meta["script"]).exists()


def test_read_through_cache_reuses_recent_value() -> None:
    cache: dict[str, tuple[float, str | None]] = {}
    calls = {"count": 0}

    def resolver() -> str:
        calls["count"] += 1
        return "cached"

    assert web_server._read_through_cache(cache, "status", resolver, ttl_seconds=60) == "cached"
    assert web_server._read_through_cache(cache, "status", resolver, ttl_seconds=60) == "cached"
    assert calls["count"] == 1


def test_get_tool_status_reports_claude_runtime_without_service_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_cached_cmd_version", lambda cmd: "2.1.183")
    monkeypatch.setattr(web_server, "_cached_npm_latest", lambda package: "2.1.193")
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "active")
    monkeypatch.setattr(web_server, "_service_status", lambda name: "inactive")

    result = web_server._get_tool_status("claude")

    assert result["status"] == "active"
    assert result["service_status"] == "inactive"
    assert result["service_manageable"] is False


def test_get_tool_status_reports_opencode_runtime_when_service_is_inactive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "active")

    def fake_opencode_status(home: Path | None = None) -> dict[str, object]:
        return {"current_version": "1.17.8", "service_active": "inactive"}

    monkeypatch.setattr("ai_config_sync.opencode_manager.opencode_status", fake_opencode_status)
    monkeypatch.setattr(
        "ai_config_sync.opencode_manager._latest_opencode_version",
        lambda: "1.17.11",
    )

    result = web_server._get_tool_status("opencode")

    assert result["installed"] == "1.17.8"
    assert result["status"] == "active"
    assert result["service_status"] == "inactive"
    assert result["service_manageable"] is True


def test_get_tool_status_reports_opencode_web_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "inactive")
    monkeypatch.setattr(web_server, "_load_settings", lambda: {})
    monkeypatch.setattr(web_server, "_service_web_details", lambda *args, **kwargs: {"url": "http://127.0.0.1:3000", "port": 3000, "host": "0.0.0.0"})

    def fake_opencode_status(home: Path | None = None) -> dict[str, object]:
        return {
            "current_version": "1.17.8",
            "service_active": "active",
            "service_name": "opencode-web.service",
            "service_path": "/etc/systemd/system/opencode-web.service",
            "launcher_path": "/home/test/.local/bin/opencode",
            "current_target": "/home/test/.local/share/opencode/releases/1.17.8",
        }

    monkeypatch.setattr("ai_config_sync.opencode_manager.opencode_status", fake_opencode_status)
    monkeypatch.setattr("ai_config_sync.opencode_manager._latest_opencode_version", lambda: "1.17.11")

    result = web_server._get_tool_status("opencode")

    assert result["web_url"] == "http://127.0.0.1:3000"
    assert result["web_port"] == 3000


def test_get_tool_status_applies_saved_web_host_override_to_displayed_web_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "inactive")
    monkeypatch.setattr(
        web_server,
        "_service_web_details",
        lambda *args, **kwargs: {"url": "http://127.0.0.1:3000", "port": 3000, "host": "0.0.0.0"},
    )
    monkeypatch.setattr(web_server, "_load_settings", lambda: {"web_host": "192.168.1.100"})

    def fake_opencode_status(home: Path | None = None) -> dict[str, object]:
        return {
            "current_version": "1.17.8",
            "service_active": "active",
            "service_name": "opencode-web.service",
            "service_path": "/etc/systemd/system/opencode-web.service",
            "launcher_path": "/home/test/.local/bin/opencode",
            "current_target": "/home/test/.local/share/opencode/releases/1.17.8",
        }

    monkeypatch.setattr("ai_config_sync.opencode_manager.opencode_status", fake_opencode_status)
    monkeypatch.setattr("ai_config_sync.opencode_manager._latest_opencode_version", lambda: "1.17.11")

    result = web_server._get_tool_status("opencode")

    assert result["web_url"] == "http://192.168.1.100:3000"
    assert result["web_host"] == "192.168.1.100"


def test_get_tool_status_applies_saved_web_host_override_to_pi_web_panel_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "active")
    monkeypatch.setattr(web_server, "_load_settings", lambda: {"web_host": "192.168.1.100"})
    monkeypatch.setattr(web_server, "_cached_npm_latest", lambda package: "0.80.2" if package == "@earendil-works/pi-coding-agent" else None)
    monkeypatch.setattr(web_server, "_cached_github_latest_redirect", lambda url: "1.21.3")
    monkeypatch.setattr(
        web_server,
        "_service_web_details",
        lambda *args, **kwargs: {"url": "http://127.0.0.1:8732", "port": 8732, "host": "0.0.0.0"},
    )
    monkeypatch.setattr(
        "ai_config_sync.pi_manager.pi_status",
        lambda home=None: {
            "version": "0.80.2",
            "launcher_path": "/home/test/.local/bin/pi",
            "install_prefix": "/home/test/.local",
        },
    )
    monkeypatch.setattr(
        "ai_config_sync.pi_web_manager.pi_web_status",
        lambda home=None: {
            "launcher_exists": True,
            "launcher_path": "/home/test/.local/bin/pi-web",
            "version": "v1.21.2",
            "service_name": "pi-web.service",
            "service_path": "/etc/systemd/system/pi-web.service",
            "service_active": "active",
        },
    )
    monkeypatch.setattr(
        "ai_config_sync.pi_package_manager.inspect_pi_packages",
        lambda **kwargs: {"managed_entries": []},
    )
    monkeypatch.setattr(
        "ai_config_sync.sync.default_paths",
        lambda repo_root, _config: SimpleNamespace(config_path=Path("/repo/shared-ai-config.json")),
    )
    monkeypatch.setattr(
        "ai_config_sync.sync.load_sync_config",
        lambda _path: SimpleNamespace(
            pi=SimpleNamespace(
                settings_path=Path("/home/test/.pi/agent/settings.json"),
                packages=(),
            )
        ),
    )

    result = web_server._get_tool_status("pi")

    assert result["web_url"] == "http://192.168.1.100:8732"
    assert result["web_host"] == "192.168.1.100"
    assert result["pi_web"]["url"] == "http://192.168.1.100:8732"
    assert result["pi_web"]["hostname"] == "192.168.1.100"


def test_find_paseo_launcher_falls_back_to_local_package_bin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = tmp_path / ".local" / "lib" / "node_modules" / "@getpaseo" / "cli" / "bin" / "paseo"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    monkeypatch.setattr(web_server, "_which_path", lambda _cmd: None)
    monkeypatch.setattr(web_server.Path, "home", lambda: tmp_path)

    result = web_server._find_paseo_launcher()

    assert result == launcher


def test_get_tool_status_reports_pi_web_and_package_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_tool_process_status", lambda tool: "active")
    monkeypatch.setattr(web_server, "_load_settings", lambda: {})
    monkeypatch.setattr(
        web_server,
        "_cached_npm_latest",
        lambda package: "0.80.2" if package == "@earendil-works/pi-coding-agent" else {"pi-subagents": "0.31.5"}.get(package),
    )
    monkeypatch.setattr(web_server, "_cached_github_latest_redirect", lambda url: "1.21.3")
    monkeypatch.setattr(
        web_server,
        "_service_web_details",
        lambda *args, **kwargs: {"url": "http://127.0.0.1:8732", "port": 8732, "host": "0.0.0.0"},
    )

    monkeypatch.setattr(
        "ai_config_sync.pi_manager.pi_status",
        lambda home=None: {
            "version": "0.80.2",
            "launcher_path": "/home/test/.local/bin/pi",
            "install_prefix": "/home/test/.local",
        },
    )
    monkeypatch.setattr(
        "ai_config_sync.pi_web_manager.pi_web_status",
        lambda home=None: {
            "launcher_exists": True,
            "launcher_path": "/home/test/.local/bin/pi-web",
            "version": "v1.21.2",
            "service_name": "pi-web.service",
            "service_path": "/etc/systemd/system/pi-web.service",
            "service_active": "active",
        },
    )
    monkeypatch.setattr(
        "ai_config_sync.pi_package_manager.inspect_pi_packages",
        lambda **kwargs: {
            "package_json_path": "/home/test/.pi/agent/npm/package.json",
            "npm_dir": "/home/test/.pi/agent/npm",
            "managed_entries": [
                {
                    "spec": "npm:pi-subagents",
                    "name": "pi-subagents",
                    "declared_version": "^0.30.0",
                    "installed_version": "0.31.2",
                    "latest_version": "0.31.5",
                    "has_update": True,
                    "installed": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "ai_config_sync.sync.default_paths",
        lambda repo_root, _config: SimpleNamespace(config_path=Path("/repo/shared-ai-config.json")),
    )
    monkeypatch.setattr(
        "ai_config_sync.sync.load_sync_config",
        lambda _path: SimpleNamespace(
            pi=SimpleNamespace(
                settings_path=Path("/home/test/.pi/agent/settings.json"),
                packages=("npm:pi-subagents",),
            )
        ),
    )

    result = web_server._get_tool_status("pi")

    assert result["service_manageable"] is True
    assert result["service_status"] == "active"
    assert result["web_url"] == "http://127.0.0.1:8732"
    assert result["pi_web"]["latest_version"] == "v1.21.3"
    assert result["pi_packages"]["managed_entries"][0]["name"] == "pi-subagents"
    assert result["pi_packages"]["managed_entries"][0]["latest_version"] == "0.31.5"


def test_paseo_status_uses_fallback_launcher_when_symlink_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = tmp_path / ".local" / "lib" / "node_modules" / "@getpaseo" / "cli" / "bin" / "paseo"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    monkeypatch.setattr(web_server, "_which_path", lambda _cmd: None)
    monkeypatch.setattr(web_server.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        web_server,
        "_command_location",
        lambda _cmd: {"launcher_path": None, "resolved_path": None, "install_root": None},
    )
    monkeypatch.setattr(web_server, "_cached_cmd_version", lambda _cmd: None)
    monkeypatch.setattr(web_server, "_cached_npm_latest", lambda _pkg: "0.1.101")
    monkeypatch.setattr(web_server, "_read_paseo_server_version", lambda _root: "0.1.101")
    monkeypatch.setattr(web_server, "_read_paseo_desktop_client_version", lambda _path: "0.1.100")

    def fake_run(args, **_kwargs):
        if args == [str(launcher), "--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="0.1.101\n", stderr="")
        if args == [str(launcher), "status", "--json"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout=json.dumps(
                    {
                        "cliVersion": "0.1.101",
                        "localDaemon": "running",
                        "home": str(tmp_path / ".paseo"),
                    }
                ),
                stderr="",
            )
        raise AssertionError(args)

    monkeypatch.setattr(web_server, "_run", fake_run)

    result = web_server._paseo_status()

    assert result["installed"] == "0.1.101"
    assert result["service_manageable"] is True
    assert result["status"] == "active"
    assert result["launcher_path"] == str(launcher)
    assert result["install_root"] == str(tmp_path / ".local")
    assert result["cli_version"] == "0.1.101"
    assert result["daemon_version"] == "0.1.101"
    assert result["desktop_client_version"] == "0.1.100"


def test_list_opencode_agent_entries_uses_config_agents(tmp_path: Path) -> None:
    config_path = tmp_path / "opencode.jsonc"
    config_path.write_text(
        json.dumps(
            {
                "agent": {
                    "skill-alpha": {"mode": "subagent"},
                    "skill-beta": {"mode": "subagent"},
                    "custom-helper": {"mode": "subagent"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = web_server._list_opencode_agent_entries(config_path, "skill-")

    assert result == ["alpha", "beta"]


def test_list_skill_dir_entries_only_returns_skill_directories(tmp_path: Path) -> None:
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)
    (skills_dir / "alpha" / "SKILL.md").write_text("alpha", encoding="utf-8")
    (skills_dir / "README.md").write_text("ignore", encoding="utf-8")
    (skills_dir / "notes").mkdir()

    result = web_server._list_skill_dir_entries(skills_dir)

    assert result == ["alpha"]


def test_list_builtin_skill_entries_reads_hidden_system_group(tmp_path: Path) -> None:
    system_dir = tmp_path / ".system" / "openai-docs"
    system_dir.mkdir(parents=True)
    (system_dir / "SKILL.md").write_text(
        "---\n"
        "description: docs helper\n"
        "---\n",
        encoding="utf-8",
    )

    result = web_server._list_builtin_skill_entries(tmp_path)

    assert result == [
        {
            "name": "openai-docs",
            "zh_label": "OpenAI 官方文档助手",
            "description": "docs helper",
            "path": str(system_dir),
            "skill_file": str(system_dir / "SKILL.md"),
            "source": "builtin",
            "group": ".system",
        }
    ]


def test_extract_skill_description_supports_folded_yaml_block() -> None:
    prompt = (
        "---\n"
        "name: frontend-design-review\n"
        "description: >\n"
        "  第一行说明。\n"
        "  第二行说明。\n"
        "---\n"
    )

    assert web_server._extract_skill_description(prompt) == "第一行说明。 第二行说明。"


def test_resolved_skill_to_entry_reloads_folded_description_from_skill_file(tmp_path: Path) -> None:
    skill_dir = tmp_path / "frontend-design-review"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\n"
        "description: >\n"
        "  第一行说明。\n"
        "  第二行说明。\n"
        "---\n",
        encoding="utf-8",
    )

    skill = SimpleNamespace(
        name="frontend-design-review",
        description=">",
        source_dir=skill_dir,
        skill_file=skill_file,
    )

    result = web_server._resolved_skill_to_entry(skill, "shared")

    assert result["description"] == "第一行说明。 第二行说明。"


def test_list_opencode_agent_entry_details_uses_known_skill_descriptions(tmp_path: Path) -> None:
    config_path = tmp_path / "opencode.jsonc"
    config_path.write_text(
        json.dumps({"agent": {"skill-alpha": {"mode": "subagent"}}}),
        encoding="utf-8",
    )

    result = web_server._list_opencode_agent_entry_details(
        config_path,
        "skill-",
        {
            "alpha": {
                "description": "alpha desc",
                "path": "/repo/skills/shared/alpha",
                "skill_file": "/repo/skills/shared/alpha/SKILL.md",
            }
        },
    )

    assert result == [
        {
            "name": "alpha",
            "zh_label": "alpha",
            "description": "alpha desc",
            "path": "/repo/skills/shared/alpha",
            "skill_file": "/repo/skills/shared/alpha/SKILL.md",
            "source": "config-agent",
        }
    ]


def test_list_mcp_servers_enriches_managed_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        mcp_servers=(
            SimpleNamespace(
                name="fetch",
                transport="stdio",
                command="/repo/tools/mcp/shared/fetch.sh",
                args=(),
                cwd=None,
                url=None,
                headers=None,
                tool_timeout_sec=None,
                direct_tools=True,
                enabled=True,
            ),
        )
    )
    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr(web_server, "_list_mcp_processes", lambda: {})
    monkeypatch.setattr(
        web_server,
        "_get_mcp_component_details",
        lambda name: {
            "managed": True,
            "component_label": "Fetch",
            "package_name": "mcp-server-fetch",
            "current_version": "2026.6.4",
            "latest_version": "2026.6.4",
            "has_update": False,
            "install_root": "/repo/vendor/mcp/fetch",
            "wrapper_path": "/repo/tools/mcp/shared/fetch.sh",
            "update_script": "/repo/scripts/mcp/update-fetch.sh",
            "manager_root": None,
            "manager_label": None,
            "version_details": None,
        },
    )

    result = web_server._list_mcp_servers()

    assert result == [
        {
            "name": "fetch",
            "type": "stdio",
            "transport": "stdio",
            "command": "/repo/tools/mcp/shared/fetch.sh",
            "args": [],
            "cwd": None,
            "url": None,
            "headers": None,
            "tool_timeout_sec": None,
            "direct_tools": True,
            "enabled": True,
            "managed": True,
            "component_label": "Fetch",
            "package_name": "mcp-server-fetch",
            "current_version": "2026.6.4",
            "latest_version": "2026.6.4",
            "has_update": False,
            "install_root": "/repo/vendor/mcp/fetch",
            "wrapper_path": "/repo/tools/mcp/shared/fetch.sh",
            "update_script": "/repo/scripts/mcp/update-fetch.sh",
            "manager_root": None,
            "manager_label": None,
            "version_details": None,
            "processes": [],
            "process_count": 0,
            "rss_bytes": 0,
            "process_groups": [],
        }
    ]


def test_list_mcp_servers_groups_generic_processes_by_project_hint(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        mcp_servers=(
            SimpleNamespace(
                name="fetch",
                transport="stdio",
                command="/repo/tools/mcp/shared/fetch.sh",
                args=(),
                cwd=None,
                url=None,
                headers=None,
                tool_timeout_sec=None,
                direct_tools=True,
                enabled=True,
            ),
        )
    )
    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr(
        web_server,
        "_list_mcp_processes",
        lambda: {
            "fetch": [
                {
                    "pid": 11,
                    "name": "python",
                    "cmd": "fetch server",
                    "kind": "server",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 2,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo/a",
                },
                {
                    "pid": 12,
                    "name": "python",
                    "cmd": "fetch server",
                    "kind": "server",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 3,
                    "parent_name": "codex",
                    "parent_cmd": "codex",
                    "parent_cwd": "/home/test",
                },
            ]
        },
    )
    monkeypatch.setattr(
        web_server,
        "_get_mcp_component_details",
        lambda name: {
            "managed": True,
            "component_label": "Fetch",
            "package_name": "mcp-server-fetch",
            "current_version": "2026.6.4",
            "latest_version": "2026.6.4",
            "has_update": False,
            "install_root": "/repo/vendor/mcp/fetch",
            "wrapper_path": "/repo/tools/mcp/shared/fetch.sh",
            "update_script": "/repo/scripts/mcp/update-fetch.sh",
            "manager_root": None,
            "manager_label": None,
            "version_details": None,
        },
    )
    monkeypatch.setattr(web_server.Path, "home", lambda: Path("/home/test"))

    result = web_server._list_mcp_servers()

    assert result[0]["process_groups"] == [
        {
            "project_root": "/repo/a",
            "label": "/repo/a",
            "process_count": 1,
            "rss_bytes": 0,
            "kind_counts": {"server": 1},
            "pids": [11],
            "processes": [
                {
                    "pid": 11,
                    "name": "python",
                    "cmd": "fetch server",
                    "kind": "server",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 2,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo/a",
                }
            ],
            "unmapped": False,
        },
        {
            "project_root": None,
            "label": "未归属会话 · codex#3",
            "process_count": 1,
            "rss_bytes": 0,
            "kind_counts": {"server": 1},
            "pids": [12],
            "processes": [
                {
                    "pid": 12,
                    "name": "python",
                    "cmd": "fetch server",
                    "kind": "server",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 3,
                    "parent_name": "codex",
                    "parent_cmd": "codex",
                    "parent_cwd": "/home/test",
                }
            ],
            "unmapped": True,
        },
    ]


def test_list_mcp_servers_groups_serena_processes_by_project(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        mcp_servers=(
            SimpleNamespace(
                name="serena",
                transport="stdio",
                command="/repo/tools/mcp/shared/serena-manager.sh",
                args=(),
                cwd=None,
                url=None,
                headers=None,
                tool_timeout_sec=None,
                direct_tools=True,
                enabled=True,
            ),
        )
    )
    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr(
        web_server,
        "_list_mcp_processes",
        lambda: {
            "serena": [
                {
                    "pid": 1001,
                    "name": "python",
                    "cmd": "runner.py start-mcp-server --project /repo-a",
                    "kind": "agent",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": "/repo-a",
                    "parent_pid": 11,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo-a",
                },
                {
                    "pid": 1002,
                    "name": "python",
                    "cmd": "-m serena_manager.launcher",
                    "kind": "manager",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 11,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo-a",
                },
            ],
        },
    )
    monkeypatch.setattr(
        web_server,
        "_read_serena_state_entries",
        lambda: [
            {
                "project_root": "/repo-a",
                "project_hash": "hash-a",
                "agent_pid": 1001,
                "endpoint_url": "http://127.0.0.1:43123/mcp",
                "status": "running",
                "started_at": 10.0,
                "last_active_at": 20.0,
                "manager_log_path": "/repo/state/hash-a/manager.log",
            }
        ],
    )
    monkeypatch.setattr(
        web_server,
        "_get_mcp_component_details",
        lambda name: {
            "managed": True,
            "component_label": "Serena Agent",
            "package_name": "serena-agent",
            "current_version": "1.5.3",
            "latest_version": "1.5.3",
            "has_update": False,
            "install_root": "/repo/vendor/mcp/serena-agent",
            "wrapper_path": "/repo/tools/mcp/shared/serena-manager.sh",
            "update_script": "/repo/scripts/mcp/update-serena-agent.sh",
            "manager_root": "/repo/vendor/mcp/serena-manager",
            "manager_label": "Serena Manager",
            "version_details": None,
        },
    )

    result = web_server._list_mcp_servers()

    assert result[0]["process_count"] == 2
    assert result[0]["process_groups"] == [
        {
            "project_root": "/repo-a",
            "project_hash": "hash-a",
            "endpoint_url": "http://127.0.0.1:43123/mcp",
            "status": "running",
            "started_at": 10.0,
            "last_active_at": 20.0,
            "manager_log_path": "/repo/state/hash-a/manager.log",
            "agent_count": 1,
            "manager_count": 1,
            "rss_bytes": 0,
            "pids": [1002, 1001],
            "processes": [
                {
                    "pid": 1002,
                    "name": "python",
                    "cmd": "-m serena_manager.launcher",
                    "kind": "manager",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 11,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo-a",
                },
                {
                    "pid": 1001,
                    "name": "python",
                    "cmd": "runner.py start-mcp-server --project /repo-a",
                    "kind": "agent",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": "/repo-a",
                    "parent_pid": 11,
                    "parent_name": "claude",
                    "parent_cmd": "claude",
                    "parent_cwd": "/repo-a",
                },
            ],
        }
    ]


def test_terminate_process_tree_kills_children_and_falls_back_to_kill(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int]] = []
    wait_calls = {"count": 0}

    class FakeProcess:
        def __init__(self, pid: int, child_pids: list[int] | None = None) -> None:
            self.pid = pid
            self._child_pids = child_pids or []
            self._running = True

        def children(self, recursive: bool = True) -> list["FakeProcess"]:
            return [procs[pid] for pid in self._child_pids]

        def terminate(self) -> None:
            calls.append(("terminate", self.pid))

        def kill(self) -> None:
            calls.append(("kill", self.pid))
            self._running = False

        def status(self) -> str:
            return "running" if self._running else "zombie"

        def is_running(self) -> bool:
            return self._running

    procs = {
        1: FakeProcess(1, [2]),
        2: FakeProcess(2),
    }

    monkeypatch.setattr(web_server.psutil, "Process", lambda pid: procs[pid])

    def fake_wait_procs(processes, timeout=0):
        wait_calls["count"] += 1
        if wait_calls["count"] == 1:
            return ([procs[2]], [procs[1]])
        return ([procs[1]], [])

    monkeypatch.setattr(web_server.psutil, "wait_procs", fake_wait_procs)

    result = web_server._terminate_process_tree([1])

    assert calls == [("terminate", 2), ("terminate", 1), ("kill", 1)]
    assert result == {"killed": [1, 2], "errors": []}


def test_get_agents_info_exposes_shared_and_target_skill_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        mcp_servers=(),
        include=("*",),
        skill_roots=(SimpleNamespace(path=Path("/repo/skills/shared")),),
        codex=SimpleNamespace(
            config_path=Path("/home/test/.codex/config.toml"),
            skills_dir=Path("/home/test/.codex/skills-shared"),
            skill_roots=(SimpleNamespace(path=Path("/repo/skills/codex")),),
            mcp_servers=(),
            global_prompt_path=Path("/home/test/.codex/AGENTS.md"),
            global_prompt_append_path=Path("/repo/prompts/codex.md"),
        ),
        claude=None,
        opencode=None,
        pi=None,
    )

    def fake_resolve_skills(roots, include, allow_missing=True):
        paths = tuple(str(root.path) for root in roots)
        if paths == ("/repo/skills/shared",):
            return [SimpleNamespace(name="shared-a"), SimpleNamespace(name="shared-b")]
        if paths == ("/repo/skills/codex",):
            return [SimpleNamespace(name="codex-only")]
        if paths == ("/repo/skills/shared", "/repo/skills/codex"):
            return [
                SimpleNamespace(name="shared-a"),
                SimpleNamespace(name="shared-b"),
                SimpleNamespace(name="codex-only"),
            ]
        return []

    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr("ai_config_sync.sync.resolve_skills", fake_resolve_skills)
    monkeypatch.setattr(web_server, "_list_skill_dir_entries", lambda _path: ["shared-a", "shared-b", "codex-only"])
    monkeypatch.setattr("ai_config_sync.sync._legacy_default_target_paths", lambda key: {"skills_dirs": (Path("/home/test/.codex/skills"),)})

    result = web_server._get_agents_info()

    assert result[0]["shared_skills"] == ["shared-a", "shared-b"]
    assert result[0]["target_specific_skills"] == ["codex-only"]
    assert result[0]["effective_managed_skills"] == ["shared-a", "shared-b", "codex-only"]


def test_get_agents_info_aggregates_runtime_and_mcp_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        mcp_servers=(SimpleNamespace(name="fetch", transport="stdio"),),
        include=("*",),
        skill_roots=(),
        codex=SimpleNamespace(
            config_path=Path("/home/test/.codex/config.toml"),
            skills_dir=Path("/home/test/.codex/skills"),
            skill_roots=(),
            mcp_servers=(),
            global_prompt_path=None,
            global_prompt_append_path=None,
        ),
        claude=None,
        opencode=None,
        pi=None,
    )

    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr("ai_config_sync.sync.resolve_skills", lambda *args, **kwargs: [])
    monkeypatch.setattr("ai_config_sync.sync._legacy_default_target_paths", lambda key: {"skills_dirs": ()})
    monkeypatch.setattr(web_server, "_list_processes", lambda: [
        {
            "tool": "codex",
            "pid": 11,
            "rss_bytes": 1024,
            "project_root": "/home/admin101/projects/2026/ai-config-sync",
            "cwd": "",
            "parent_cwd": "/home/admin101",
            "ancestor_cwds": [],
            "descendant_cwds": [],
        }
    ])
    monkeypatch.setattr(web_server, "_list_mcp_processes", lambda: {
        "fetch": [
            {
                "pid": 21,
                "rss_bytes": 2048,
                "project_root": None,
                "parent_cwd": "/home/admin101/projects/2026/ai-config-sync",
                "cwd": None,
                "ancestor_cwds": [],
                "descendant_cwds": [],
                "tool": "codex",
            }
        ]
    })

    result = web_server._get_agents_info()

    assert result[0]["project_root"] == "/home/admin101/projects/2026/ai-config-sync"
    assert result[0]["process_count"] == 1
    assert result[0]["process_rss_bytes"] == 1024
    assert result[0]["mcp_process_count"] == 1
    assert result[0]["mcp_rss_bytes"] == 2048
    assert result[0]["total_rss_bytes"] == 3072


def test_save_prompt_source_writes_scope_and_refreshes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    shared = tmp_path / "shared.md"
    overlay = tmp_path / "overlay.md"
    effective = tmp_path / "AGENTS.md"
    shared.write_text("old shared\n", encoding="utf-8")
    overlay.write_text("old overlay\n", encoding="utf-8")
    config = SimpleNamespace(
        global_prompt_path=shared,
        codex=SimpleNamespace(
            global_prompt_path=effective,
            global_prompt_append_path=overlay,
        ),
        claude=None,
        opencode=None,
        pi=None,
    )

    monkeypatch.setattr(web_server, "_load_sync_config", lambda: config)
    monkeypatch.setattr(web_server, "_get_prompt_payload", lambda tool: {"tool": tool, "effective": {"text": "new"}})

    web_server._save_prompt_source("codex", "overlay", "new overlay\n")

    assert overlay.read_text(encoding="utf-8") == "new overlay\n"


def test_is_runtime_process_filters_codex_noise_and_claude_probe() -> None:
    assert web_server._is_runtime_process(
        "codex",
        name="owjdxb",
        cmdline=["/home/admin101/.codex/owjdxb/bin/owjdxb"],
    ) is False
    assert web_server._is_runtime_process(
        "claude",
        name="claude",
        cmdline=["/home/admin101/.local/bin/claude", "auth", "status", "--json"],
    ) is False
    assert web_server._is_runtime_process(
        "opencode",
        name="opencode",
        cmdline=["/home/admin101/.local/bin/opencode", "serve", "--port", "3000"],
    ) is True


def test_project_hint_prefers_ancestor_project_root_for_codex_session() -> None:
    result = web_server._project_hint_from_process(
        {
            "tool": "codex",
            "project_root": None,
            "cwd": None,
            "parent_cwd": "/home/admin101",
            "ancestor_cwds": [
                "/home/admin101",
                "/home/admin101/projects/2026/ai-config-sync",
            ],
            "descendant_cwds": [],
        }
    )

    assert result == "/home/admin101/projects/2026/ai-config-sync"


def test_project_hint_ignores_project_grouping_for_paseo() -> None:
    result = web_server._project_hint_from_process(
        {
            "tool": "paseo",
            "project_root": None,
            "cwd": "/home/admin101/projects/2026/ai-config-sync",
            "parent_cwd": "/home/admin101/projects/2026/ai-config-sync",
            "ancestor_cwds": ["/home/admin101/projects/2026/ai-config-sync"],
            "descendant_cwds": [],
        }
    )

    assert result is None


def test_build_generic_mcp_process_groups_uses_ancestor_project_hint_for_codex() -> None:
    result = web_server._build_generic_mcp_process_groups(
        [
            {
                "pid": 12,
                "name": "python",
                "cmd": "fetch server",
                "kind": "server",
                "raw_status": "sleeping",
                "state_label": "等待中",
                "state_tone": "blue",
                "project_root": None,
                "parent_pid": 3,
                "parent_name": "codex",
                "parent_cmd": "codex",
                "parent_cwd": "/home/admin101",
                "ancestor_cwds": [
                    "/home/admin101",
                    "/home/admin101/projects/2026/ai-config-sync",
                ],
                "descendant_cwds": [],
                "rss_bytes": 2048,
                "tool": "codex",
            }
        ]
    )

    assert result == [
        {
            "project_root": "/home/admin101/projects/2026/ai-config-sync",
            "label": "/home/admin101/projects/2026/ai-config-sync",
            "process_count": 1,
            "rss_bytes": 2048,
            "kind_counts": {"server": 1},
            "pids": [12],
            "processes": [
                {
                    "pid": 12,
                    "name": "python",
                    "cmd": "fetch server",
                    "kind": "server",
                    "raw_status": "sleeping",
                    "state_label": "等待中",
                    "state_tone": "blue",
                    "project_root": None,
                    "parent_pid": 3,
                    "parent_name": "codex",
                    "parent_cmd": "codex",
                    "parent_cwd": "/home/admin101",
                    "ancestor_cwds": [
                        "/home/admin101",
                        "/home/admin101/projects/2026/ai-config-sync",
                    ],
                    "descendant_cwds": [],
                    "rss_bytes": 2048,
                    "tool": "codex",
                }
            ],
            "unmapped": False,
        }
    ]


def test_sum_rss_bytes_ignores_missing_values() -> None:
    result = web_server._sum_rss_bytes(
        [
            {"pid": 1, "rss_bytes": 1024},
            {"pid": 2, "rss_bytes": None},
            {"pid": 3},
            {"pid": 4, "rss_bytes": 2048},
        ]
    )

    assert result == 3072


def test_project_hint_uses_descendant_project_root_for_codex_session() -> None:
    result = web_server._project_hint_from_process(
        {
            "tool": "codex",
            "project_root": None,
            "cwd": None,
            "parent_cwd": "/home/admin101",
            "ancestor_cwds": ["/home/admin101"],
            "descendant_cwds": [
                "/home/admin101/projects/2026/ai-config-sync/vendor/mcp/node-repl-linux",
                "/home/admin101/projects/2026/ai-config-sync",
            ],
        }
    )

    assert result == "/home/admin101/projects/2026/ai-config-sync"


def test_api_self_status_reports_activating_with_port_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = subprocess.CompletedProcess(
        ["systemctl", "--user", "is-active", "ai-config-sync-web.service"],
        0,
        stdout="activating\n",
        stderr="",
    )
    enabled = subprocess.CompletedProcess(
        ["systemctl", "--user", "is-enabled", "ai-config-sync-web.service"],
        0,
        stdout="enabled\n",
        stderr="",
    )
    show = subprocess.CompletedProcess(
        ["systemctl", "--user", "show", "ai-config-sync-web.service"],
        0,
        stdout="ActiveState=activating\nSubState=auto-restart\nResult=exit-code\nExecMainStatus=1\nExecMainCode=1\n",
        stderr="",
    )
    journal = subprocess.CompletedProcess(
        ["journalctl", "--user", "-u", "ai-config-sync-web.service", "-n", "20", "--no-pager"],
        0,
        stdout="ERROR: [Errno 98] error while attempting to bind on address ('0.0.0.0', 9731): address already in use\n",
        stderr="",
    )

    def fake_user_systemctl(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("is-active", "ai-config-sync-web.service"):
            return active
        if args[:2] == ("is-enabled", "ai-config-sync-web.service"):
            return enabled
        if args[:2] == ("show", "ai-config-sync-web.service"):
            return show
        raise AssertionError(args)

    monkeypatch.setattr(web_server, "_user_systemctl", fake_user_systemctl)
    monkeypatch.setattr(web_server, "_run", lambda *args, **kwargs: journal)

    result = web_server._self_status_payload()

    assert result["active"] == "activating"
    assert result["state_label"] == "守护重启中"
    assert result["can_start"] is False
    assert result["issue"] == "port-in-use"


def test_project_hint_does_not_treat_home_dir_as_project() -> None:
    result = web_server._project_hint_from_process(
        {
            "tool": "opencode",
            "project_root": None,
            "cwd": None,
            "parent_cwd": "/home/admin101",
            "ancestor_cwds": ["/home/admin101"],
            "descendant_cwds": [],
        }
    )

    assert result is None


def test_paseo_agent_project_root_reads_opencode_agent_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    paseo_root = tmp_path / ".paseo" / "agents" / "home-admin101-projects-2026-ai-config-sync"
    paseo_root.mkdir(parents=True)
    agent_id = "84b66a15-06a6-4edb-85d7-01ed96a50801"
    (paseo_root / f"{agent_id}.json").write_text(
        json.dumps(
            {
                "id": agent_id,
                "provider": "opencode",
                "cwd": "/home/admin101/projects/2026/ai-config-sync",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_server.Path, "home", lambda: tmp_path)

    result = web_server._paseo_agent_project_root(agent_id)

    assert result == "/home/admin101/projects/2026/ai-config-sync"


def test_list_processes_uses_paseo_agent_project_root_for_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.info = {
                "pid": 101,
                "name": "codex",
                "cmdline": ["/usr/local/bin/codex", "app-server", "--enable", "goals"],
                "status": "sleeping",
                "create_time": 0.0,
            }

        def cwd(self) -> str:
            return "/home/admin101"

        def environ(self) -> dict[str, str]:
            return {"PASEO_AGENT_ID": "agent-1"}

    monkeypatch.setattr(web_server.psutil, "process_iter", lambda _attrs: [FakeProcess()])
    monkeypatch.setattr(web_server, "_process_parent_meta", lambda _proc: {"parent_pid": None, "parent_name": None, "parent_cmd": None, "parent_cwd": None})
    monkeypatch.setattr(web_server, "_process_ancestor_cwds", lambda _proc: [])
    monkeypatch.setattr(web_server, "_process_descendant_cwds", lambda _proc: [])
    monkeypatch.setattr(web_server, "_paseo_agent_project_root", lambda agent_id: "/home/admin101/projects/2026/beiyuan" if agent_id == "agent-1" else None)

    result = web_server._list_processes()

    assert result == [
        {
            "tool": "codex",
            "pid": 101,
            "name": "codex",
            "cmd": "/usr/local/bin/codex app-server --enable goals",
            "cwd": "",
            "kind": "app-server",
            "status": "sleeping",
            "rss_bytes": 0,
            "raw_status": "sleeping",
            "state_label": "等待中",
            "state_tone": "blue",
            "project_root": "/home/admin101/projects/2026/beiyuan",
            "parent_pid": None,
            "parent_name": None,
            "parent_cmd": None,
            "parent_cwd": None,
            "ancestor_cwds": [],
            "descendant_cwds": [],
        }
    ]


def test_annotate_paseo_processes_marks_listening_daemon_chain_as_primary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_listening_pids", lambda: {103})

    processes = [
        {
            "tool": "paseo",
            "pid": 101,
            "parent_pid": 1,
            "name": "node",
            "cmd": "paseo daemon start --foreground",
            "kind": "daemon-launcher",
        },
        {
            "tool": "paseo",
            "pid": 102,
            "parent_pid": 101,
            "name": "Paseo Supervisor",
            "cmd": "Paseo Supervisor",
            "kind": "supervisor",
        },
        {
            "tool": "paseo",
            "pid": 103,
            "parent_pid": 102,
            "name": "Paseo Daemon",
            "cmd": "Paseo Daemon",
            "kind": "daemon",
        },
        {
            "tool": "paseo",
            "pid": 104,
            "parent_pid": 103,
            "name": "node",
            "cmd": "terminal-worker-process.js",
            "kind": "terminal-worker",
        },
        {
            "tool": "paseo",
            "pid": 201,
            "parent_pid": 1,
            "name": "Paseo Supervisor",
            "cmd": "Paseo Supervisor",
            "kind": "supervisor",
        },
        {
            "tool": "paseo",
            "pid": 202,
            "parent_pid": 201,
            "name": "node",
            "cmd": "daemon-worker.js",
            "kind": "daemon-worker",
        },
    ]

    result = web_server._annotate_paseo_processes(processes)
    by_pid = {item["pid"]: item for item in result}

    assert by_pid[101]["primary"] is True
    assert by_pid[102]["primary"] is True
    assert by_pid[103]["primary"] is True
    assert by_pid[104]["primary"] is True
    assert by_pid[201]["residual"] is True
    assert by_pid[202]["residual"] is True


def test_annotate_paseo_processes_falls_back_to_latest_daemon_when_no_listener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_server, "_listening_pids", lambda: set())

    processes = [
        {
            "tool": "paseo",
            "pid": 301,
            "parent_pid": 1,
            "name": "node",
            "cmd": "paseo daemon start --foreground",
            "kind": "daemon-launcher",
        },
        {
            "tool": "paseo",
            "pid": 302,
            "parent_pid": 301,
            "name": "Paseo Daemon",
            "cmd": "Paseo Daemon",
            "kind": "daemon",
        },
        {
            "tool": "paseo",
            "pid": 401,
            "parent_pid": 1,
            "name": "node",
            "cmd": "paseo daemon start --foreground",
            "kind": "daemon-launcher",
        },
        {
            "tool": "paseo",
            "pid": 402,
            "parent_pid": 401,
            "name": "Paseo Daemon",
            "cmd": "Paseo Daemon",
            "kind": "daemon",
        },
    ]

    result = web_server._annotate_paseo_processes(processes)
    by_pid = {item["pid"]: item for item in result}

    assert by_pid[401]["primary"] is True
    assert by_pid[402]["primary"] is True
    assert by_pid[301]["residual"] is True
    assert by_pid[302]["residual"] is True
