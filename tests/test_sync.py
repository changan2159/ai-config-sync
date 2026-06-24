import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

import ai_config_sync.cli as cli_module
import ai_config_sync.mcp_updates as mcp_updates_module
import ai_config_sync.sync as sync_module
from ai_config_sync.sync import (
    McpServerConfig,
    SyncError,
    SyncPaths,
    add_mcp_server,
    compute_fingerprint,
    default_paths,
    install_service,
    load_sync_config,
    remove_mcp_server,
    resolve_skills,
    start_service,
    stop_service,
    sync_clients,
    watch_loop,
)


def write_skill(root: Path, name: str, description: str) -> None:
    path = root / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nUse {name}.\n",
        encoding="utf-8",
    )


def write_config(
    path: Path,
    skill_roots: list[dict],
    targets: dict,
    servers: dict,
    global_prompt_path: str | None = None,
    include: list[str] | None = None,
) -> None:
    payload = {
        "mcpServers": servers,
        "skillRoots": skill_roots,
        "include": include or ["*"],
        "targets": targets,
    }
    if global_prompt_path is not None:
        payload["globalPromptPath"] = global_prompt_path
    path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )


def test_sync_clients_updates_targets_and_removes_old_entries(tmp_path: Path) -> None:
    core_root = tmp_path / "core"
    plugin_root = tmp_path / "plugin"
    write_skill(core_root, "alpha", "Alpha skill")
    write_skill(plugin_root, "beta", "Beta skill")

    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    codex_overlay = tmp_path / "codex-overlay.md"
    claude_overlay = tmp_path / "claude-overlay.md"
    opencode_overlay = tmp_path / "opencode-overlay.md"
    pi_overlay = tmp_path / "pi-overlay.md"
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_prompt = tmp_path / "codex" / "AGENTS.md"
    claude_prompt = tmp_path / "claude" / "CLAUDE.md"
    opencode_prompt = tmp_path / "opencode" / "AGENTS.md"
    pi_prompt = tmp_path / "pi" / "AGENTS.md"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text('{"mcpServers":{"manual":{"type":"stdio","command":"/bin/true","args":[],"env":{}}}}\n', encoding="utf-8")
    opencode_config.parent.mkdir(parents=True)
    opencode_config.write_text('{"$schema":"https://opencode.ai/config.json"}\n', encoding="utf-8")
    pi_settings.parent.mkdir(parents=True)
    pi_settings.write_text('{"theme":"dark","packages":["keep-me"],"skills":["/manual/skills"]}\n', encoding="utf-8")
    pi_mcp_config.parent.mkdir(parents=True)
    pi_mcp_config.write_text('{"mcpServers":{"manual":{"command":"/bin/true"}}}\n', encoding="utf-8")
    shared_prompt.write_text("Shared global prompt.\n", encoding="utf-8")
    codex_overlay.write_text("Codex overlay.\n", encoding="utf-8")
    claude_overlay.write_text("Claude overlay.\n", encoding="utf-8")
    opencode_overlay.write_text("OpenCode overlay.\n", encoding="utf-8")
    pi_overlay.write_text("Pi overlay.\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[
            {"path": str(core_root), "prefix": ""},
            {"path": str(plugin_root), "prefix": "plugin:"},
        ],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(codex_prompt),
                "globalPromptAppendPath": str(codex_overlay),
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
                "globalPromptPath": str(claude_prompt),
                "globalPromptAppendPath": str(claude_overlay),
            },
            "opencode": {
                "configPath": str(opencode_config),
                "agentPrefix": "skill-",
                "globalPromptPath": str(opencode_prompt),
                "globalPromptAppendPath": str(opencode_overlay),
            },
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter"],
                "enableSkillCommands": True,
                "globalPromptPath": str(pi_prompt),
                "globalPromptAppendPath": str(pi_overlay),
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo", "args": ["hello"]}},
        global_prompt_path=str(shared_prompt),
    )

    result = sync_clients(load_sync_config(config_path), state_path)
    assert result["skills"] == ["alpha", "plugin:beta"]
    assert (tmp_path / "claude" / "skills" / "plugin:beta").is_symlink()
    assert (tmp_path / "pi" / "skills" / "plugin:beta").is_symlink()
    assert codex_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nCodex overlay.\n"
    assert claude_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nClaude overlay.\n"
    assert opencode_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nOpenCode overlay.\n"
    assert pi_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nPi overlay.\n"
    opencode = json.loads(opencode_config.read_text(encoding="utf-8"))
    assert "skill-plugin:beta" in opencode["agent"]
    pi_settings_data = json.loads(pi_settings.read_text(encoding="utf-8"))
    assert pi_settings_data["theme"] == "dark"
    assert pi_settings_data["packages"] == ["keep-me", "npm:pi-mcp-adapter"]
    assert pi_settings_data["skills"] == ["/manual/skills", str(tmp_path / "pi" / "skills")]
    assert pi_settings_data["enableSkillCommands"] is True
    pi_mcp_data = json.loads(pi_mcp_config.read_text(encoding="utf-8"))
    assert pi_mcp_data["mcpServers"]["manual"] == {"command": "/bin/true"}
    assert pi_mcp_data["mcpServers"]["demo"]["command"] == "/bin/echo"
    assert pi_mcp_data["mcpServers"]["demo"]["args"] == ["hello"]
    assert result["targets"]["codex"]["global_prompt_path"] == str(codex_prompt)
    assert result["targets"]["codex"]["global_prompt_append_path"] == str(codex_overlay)
    assert result["targets"]["claude"]["global_prompt_path"] == str(claude_prompt)
    assert result["targets"]["claude"]["global_prompt_append_path"] == str(claude_overlay)
    assert result["targets"]["opencode"]["global_prompt_path"] == str(opencode_prompt)
    assert result["targets"]["opencode"]["global_prompt_append_path"] == str(opencode_overlay)
    assert result["targets"]["pi"]["settings_path"] == str(pi_settings)
    assert result["targets"]["pi"]["mcp_config_path"] == str(pi_mcp_config)
    assert result["targets"]["pi"]["global_prompt_path"] == str(pi_prompt)
    assert result["targets"]["pi"]["global_prompt_append_path"] == str(pi_overlay)

    write_config(
        config_path,
        skill_roots=[{"path": str(core_root), "prefix": ""}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(codex_prompt),
                "globalPromptAppendPath": str(codex_overlay),
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
                "globalPromptPath": str(claude_prompt),
                "globalPromptAppendPath": str(claude_overlay),
            },
            "opencode": {
                "configPath": str(opencode_config),
                "agentPrefix": "skill-",
                "globalPromptPath": str(opencode_prompt),
                "globalPromptAppendPath": str(opencode_overlay),
            },
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter"],
                "enableSkillCommands": True,
                "globalPromptPath": str(pi_prompt),
                "globalPromptAppendPath": str(pi_overlay),
            },
        },
        servers={"demo2": {"type": "stdio", "command": "/bin/true"}},
        global_prompt_path=str(shared_prompt),
    )
    result = sync_clients(load_sync_config(config_path), state_path)
    assert not (tmp_path / "claude" / "skills" / "plugin:beta").exists()
    assert not (tmp_path / "pi" / "skills" / "plugin:beta").exists()
    text = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.demo]" not in text
    assert "[mcp_servers.demo2]" in text
    pi_mcp_data = json.loads(pi_mcp_config.read_text(encoding="utf-8"))
    assert "demo" not in pi_mcp_data["mcpServers"]
    assert "demo2" in pi_mcp_data["mcpServers"]


def test_sync_clients_manages_pi_models_and_defaults(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_models = tmp_path / "pi" / "models.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    pi_settings.write_text(
        json.dumps(
            {
                "theme": "light",
                "defaultProvider": "ollama-host",
                "defaultModel": "devstral-small-2",
                "packages": [],
                "skills": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pi_models.write_text(
        json.dumps(
            {
                "providers": {
                    "ollama-host": {
                        "baseUrl": "http://127.0.0.1:11434/v1",
                        "api": "openai-completions",
                        "apiKey": "ollama",
                        "models": [{"id": "devstral-small-2"}],
                    }
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    pi_mcp_config.write_text("{}\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter"],
                "defaultProvider": "chris",
                "defaultModel": "gpt-5.4",
                "enableSkillCommands": True,
                "providers": {
                    "chris": {
                        "baseUrl": "http://38.145.220.6:9000/v1",
                        "api": "openai-responses",
                        "apiKey": "$OPENAI_API_KEY",
                        "authHeader": True,
                        "models": [
                            {
                                "id": "gpt-5.4",
                                "name": "GPT-5.4 (Relay)",
                                "reasoning": True,
                                "input": ["text", "image"],
                                "contextWindow": 400000,
                                "maxTokens": 128000,
                                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
                            }
                        ],
                    }
                },
            }
        },
        servers={},
    )

    result = sync_clients(load_sync_config(config_path), state_path)

    pi_settings_data = json.loads(pi_settings.read_text(encoding="utf-8"))
    assert pi_settings_data["theme"] == "light"
    assert pi_settings_data["defaultProvider"] == "chris"
    assert pi_settings_data["defaultModel"] == "gpt-5.4"
    assert pi_settings_data["enableSkillCommands"] is True
    assert pi_settings_data["packages"] == ["npm:pi-mcp-adapter"]

    pi_models_data = json.loads(pi_models.read_text(encoding="utf-8"))
    assert "ollama-host" in pi_models_data["providers"]
    assert pi_models_data["providers"]["chris"]["api"] == "openai-responses"
    assert pi_models_data["providers"]["chris"]["apiKey"] == "$OPENAI_API_KEY"
    assert pi_models_data["providers"]["chris"]["models"][0]["id"] == "gpt-5.4"

    assert result["targets"]["pi"]["models_path"] == str(pi_models)
    assert result["targets"]["pi"]["providers"] == ["chris"]
    assert result["targets"]["pi"]["default_provider"] == "chris"
    assert result["targets"]["pi"]["default_model"] == "gpt-5.4"

    write_config(config_path, skill_roots=[{"path": str(root)}], targets={}, servers={})
    sync_clients(load_sync_config(config_path), state_path)

    cleared_settings = json.loads(pi_settings.read_text(encoding="utf-8"))
    assert "defaultProvider" not in cleared_settings
    assert "defaultModel" not in cleared_settings
    assert "enableSkillCommands" not in cleared_settings

    cleared_models = json.loads(pi_models.read_text(encoding="utf-8"))
    assert "chris" not in cleared_models["providers"]
    assert "ollama-host" in cleared_models["providers"]


def test_sync_clients_runs_managed_pi_package_sync(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    pi_settings.write_text("{}\n", encoding="utf-8")
    pi_mcp_config.write_text("{}\n", encoding="utf-8")
    calls: list[tuple[Path, tuple[str, ...], list[str]]] = []

    def fake_sync_pi_packages(
        *,
        settings_path: Path,
        packages: tuple[str, ...],
        previous_packages: list[str],
    ) -> dict[str, object]:
        calls.append((settings_path, packages, previous_packages))
        return {"installed": ["npm:pi-subagents"], "removed": [], "installed_package_names": ["pi-subagents"]}

    monkeypatch.setattr(sync_module, "sync_pi_packages", fake_sync_pi_packages)

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter", "npm:pi-subagents"],
            },
        },
        servers={},
    )

    result = sync_clients(load_sync_config(config_path), state_path)

    assert calls == [(pi_settings, ("npm:pi-mcp-adapter", "npm:pi-subagents"), [])]
    assert result["targets"]["pi"]["package_sync"] == {
        "installed": ["npm:pi-subagents"],
        "removed": [],
        "installed_package_names": ["pi-subagents"],
    }


def test_sync_clients_uninstalls_managed_pi_packages_when_pi_target_is_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    pi_settings.write_text("{}\n", encoding="utf-8")
    pi_mcp_config.write_text("{}\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter", "npm:pi-subagents"],
            },
        },
        servers={},
    )
    sync_clients(load_sync_config(config_path), state_path)

    calls: list[tuple[Path, tuple[str, ...], list[str]]] = []

    def fake_sync_pi_packages(
        *,
        settings_path: Path,
        packages: tuple[str, ...],
        previous_packages: list[str],
    ) -> dict[str, object]:
        calls.append((settings_path, packages, previous_packages))
        return {"installed": [], "removed": previous_packages, "installed_package_names": []}

    monkeypatch.setattr(sync_module, "sync_pi_packages", fake_sync_pi_packages)
    write_config(config_path, skill_roots=[{"path": str(root)}], targets={}, servers={})

    sync_clients(load_sync_config(config_path), state_path)

    assert calls == [
        (
            pi_settings,
            (),
            ["npm:pi-mcp-adapter", "npm:pi-subagents"],
        )
    ]


def test_compute_fingerprint_changes_when_global_prompt_changes(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    config_path = tmp_path / "shared-ai-config.json"
    write_skill(root, "alpha", "Alpha")
    shared_prompt.write_text("Prompt v1\n", encoding="utf-8")
    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={},
        servers={},
        global_prompt_path=str(shared_prompt),
    )

    before = compute_fingerprint(config_path)
    shared_prompt.write_text("Prompt v2\n", encoding="utf-8")
    after = compute_fingerprint(config_path)

    assert after != before


def test_compute_fingerprint_changes_when_target_overlay_changes(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    codex_overlay = tmp_path / "codex-overlay.md"
    config_path = tmp_path / "shared-ai-config.json"
    write_skill(root, "alpha", "Alpha")
    shared_prompt.write_text("Prompt v1\n", encoding="utf-8")
    codex_overlay.write_text("Overlay v1\n", encoding="utf-8")
    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(tmp_path / "codex" / "config.toml"),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(tmp_path / "codex" / "AGENTS.md"),
                "globalPromptAppendPath": str(codex_overlay),
            },
        },
        servers={},
        global_prompt_path=str(shared_prompt),
    )

    before = compute_fingerprint(config_path)
    codex_overlay.write_text("Overlay v2\n", encoding="utf-8")
    after = compute_fingerprint(config_path)

    assert after != before


def test_add_remove_mcp_server_updates_source_config(tmp_path: Path) -> None:
    config_path = tmp_path / "shared-ai-config.json"
    config_path.write_text('{"mcpServers":{},"skillRoots":[],"include":["*"],"targets":{}}\n', encoding="utf-8")
    add_mcp_server(config_path, McpServerConfig(name="demo", transport="stdio", command="/bin/echo", args=("hi",)))
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["mcpServers"]["demo"]["args"] == ["hi"]
    remove_mcp_server(config_path, "demo")
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert "demo" not in data["mcpServers"]


def test_service_install_start_stop(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    paths = default_paths(repo_root)
    calls: list[tuple[str, ...]] = []

    def fake_run(args, capture_output, text, encoding, check):  # type: ignore[no-untyped-def]
        calls.append(tuple(args))
        if tuple(args[-2:]) == ("is-active", paths.service_name):
            return subprocess.CompletedProcess(args, 0, stdout="active\n", stderr="")
        if tuple(args[-2:]) == ("is-enabled", paths.service_name):
            return subprocess.CompletedProcess(args, 0, stdout="enabled\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    install_service(paths, 2.0)
    start_service(paths, 2.0)
    stop_service(paths)
    assert ("systemctl", "--user", "enable", "--now", paths.service_name) in calls


def test_resolve_skills_uses_all_roots_with_prefixes(tmp_path: Path) -> None:
    root_a = tmp_path / "a"
    root_b = tmp_path / "b"
    write_skill(root_a, "alpha", "Alpha")
    write_skill(root_b, "beta", "Beta")
    config_path = tmp_path / "shared-ai-config.json"
    write_config(config_path, [{"path": str(root_a)}, {"path": str(root_b), "prefix": "x:"}], {}, {})
    config = load_sync_config(config_path)
    names = [skill.name for skill in resolve_skills(config.skill_roots, config.include)]
    assert names == ["alpha", "x:beta"]


def test_load_sync_config_expands_repo_and_home_placeholders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path = repo_root / "shared-ai-config.json"
    payload = {
        "mcpServers": {
            "demo": {
                "type": "stdio",
                "command": "${REPO_ROOT}/tools/mcp/shared/demo.sh",
                "cwd": "${HOME}/workspace",
                "env": {"DATA_ROOT": "${REPO_ROOT}/data"},
            }
        },
        "skillRoots": [
            {
                "path": "${REPO_ROOT}/skills/shared",
            }
        ],
        "include": ["*"],
        "globalPromptPath": "${REPO_ROOT}/prompts/shared-global-prompt.md",
        "targets": {
            "codex": {
                "configPath": "${HOME}/.codex/config.toml",
                "skillsDir": "${HOME}/.codex/skills-shared",
                "globalPromptPath": "${HOME}/.codex/AGENTS.md",
                "globalPromptAppendPath": "${REPO_ROOT}/prompts/codex-global-prompt.md",
            },
            "pi": {
                "settingsPath": "${HOME}/.pi/agent/settings.json",
                "mcpConfigPath": "${HOME}/.config/mcp/mcp.json",
                "skillsDir": "${HOME}/.pi/agent/skills-shared",
                "packages": ["npm:pi-mcp-adapter"],
                "enableSkillCommands": True,
                "globalPromptPath": "${HOME}/.pi/agent/AGENTS.md",
                "globalPromptAppendPath": "${REPO_ROOT}/prompts/pi-global-prompt.md",
            },
        },
    }
    config_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    config = load_sync_config(config_path)

    assert config.skill_roots[0].path == repo_root / "skills" / "shared"
    assert config.mcp_servers[0].command == str(repo_root / "tools" / "mcp" / "shared" / "demo.sh")
    assert config.mcp_servers[0].cwd == str(home / "workspace")
    assert config.mcp_servers[0].env == {"DATA_ROOT": str(repo_root / "data")}
    assert config.global_prompt_path == repo_root / "prompts" / "shared-global-prompt.md"
    assert config.codex is not None
    assert config.codex.config_path == home / ".codex" / "config.toml"
    assert config.codex.global_prompt_append_path == repo_root / "prompts" / "codex-global-prompt.md"
    assert config.pi is not None
    assert config.pi.settings_path == home / ".pi" / "agent" / "settings.json"
    assert config.pi.mcp_config_path == home / ".config" / "mcp" / "mcp.json"
    assert config.pi.skills_dir == home / ".pi" / "agent" / "skills-shared"
    assert config.pi.packages == ("npm:pi-mcp-adapter",)
    assert config.pi.enable_skill_commands is True
    assert config.pi.global_prompt_append_path == repo_root / "prompts" / "pi-global-prompt.md"


def test_repo_shared_config_includes_expected_managed_pi_packages() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = load_sync_config(repo_root / "shared-ai-config.json")

    assert config.codex is not None
    assert config.codex.skill_roots == (
        sync_module.SkillRootConfig(path=repo_root / "skills" / "codex", prefix="", exclude=()),
    )
    assert config.skill_roots == (
        sync_module.SkillRootConfig(path=repo_root / "skills" / "shared", prefix="", exclude=()),
    )
    assert config.claude is not None
    assert config.opencode is not None
    assert config.pi is not None
    assert config.pi.packages == (
        "npm:pi-mcp-adapter",
        "npm:@narumitw/pi-plan-mode",
        "npm:pi-subagents",
        "npm:pi-nano-context",
    )
    assert config.pi.enable_skill_commands is True


def test_sync_clients_applies_target_specific_skill_roots_and_mcp_servers(tmp_path: Path) -> None:
    shared_root = tmp_path / "skills"
    codex_root = tmp_path / "skills-codex"
    write_skill(shared_root, "alpha", "Alpha skill")
    write_skill(codex_root, "codex-subagent", "Codex-only subagent skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    codex_config.parent.mkdir(parents=True)
    claude_config.parent.mkdir(parents=True)
    opencode_config.parent.mkdir(parents=True)
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.write_text("{}\n", encoding="utf-8")
    pi_settings.write_text("{}\n", encoding="utf-8")
    pi_mcp_config.write_text("{}\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(shared_root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "skillRoots": [{"path": str(codex_root)}],
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
                "mcpServers": {
                    "claude-only": {"type": "stdio", "command": "/bin/true"},
                },
            },
            "opencode": {
                "configPath": str(opencode_config),
                "agentPrefix": "skill-",
                "mcpServers": {
                    "opencode-only": {"type": "stdio", "command": "/bin/printf"},
                },
            },
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(tmp_path / "pi" / "skills"),
                "packages": ["npm:pi-mcp-adapter"],
                "mcpServers": {
                    "pi-only": {"type": "stdio", "command": "/bin/date"},
                },
            },
        },
        servers={
            "shared": {"type": "stdio", "command": "/bin/echo"},
        },
    )

    result = sync_clients(load_sync_config(config_path), state_path)

    # target-specific skill present only where expected
    assert (tmp_path / "codex" / "skills" / "codex-subagent").is_symlink()
    assert not (tmp_path / "claude" / "skills" / "codex-subagent").exists()
    assert not (tmp_path / "pi" / "skills" / "codex-subagent").exists()

    # shared skill present in every target that uses a skills dir
    assert (tmp_path / "codex" / "skills" / "alpha").is_symlink()
    assert (tmp_path / "claude" / "skills" / "alpha").is_symlink()
    assert (tmp_path / "pi" / "skills" / "alpha").is_symlink()

    claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
    assert set(claude_data["mcpServers"]) == {"shared", "claude-only"}

    opencode_data = sync_module._load_jsonc(opencode_config)
    assert "skill-codex-subagent" not in opencode_data["agent"]
    assert set(opencode_data["mcp"]) == {"shared", "opencode-only"}

    pi_mcp_data = json.loads(pi_mcp_config.read_text(encoding="utf-8"))
    assert set(pi_mcp_data["mcpServers"]) == {"shared", "pi-only"}

    assert result["targets"]["opencode"]["agents"] == ["skill-alpha"]


def test_sync_clients_include_allows_target_specific_skill_names(tmp_path: Path) -> None:
    shared_root = tmp_path / "skills"
    codex_root = tmp_path / "skills-codex"
    write_skill(shared_root, "alpha", "Alpha skill")
    write_skill(codex_root, "codex-subagent", "Codex-only subagent skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    codex_config.parent.mkdir(parents=True)
    claude_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.write_text("{}\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(shared_root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "skillRoots": [{"path": str(codex_root)}],
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
            },
        },
        servers={},
        include=["alpha", "codex-subagent"],
    )

    result = sync_clients(load_sync_config(config_path), state_path)

    assert result["skills"] == ["alpha"]
    assert (tmp_path / "codex" / "skills" / "alpha").is_symlink()
    assert (tmp_path / "codex" / "skills" / "codex-subagent").is_symlink()
    assert (tmp_path / "claude" / "skills" / "alpha").is_symlink()
    assert not (tmp_path / "claude" / "skills" / "codex-subagent").exists()


def test_sync_clients_rejects_include_names_missing_from_all_roots(tmp_path: Path) -> None:
    shared_root = tmp_path / "skills"
    write_skill(shared_root, "alpha", "Alpha skill")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(shared_root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
            },
        },
        servers={},
        include=["alpha", "missing-skill"],
    )

    with pytest.raises(SyncError, match="missing-skill"):
        sync_clients(load_sync_config(config_path), state_path)


def test_compute_fingerprint_changes_for_target_specific_skill_files(tmp_path: Path) -> None:
    shared_root = tmp_path / "skills"
    codex_root = tmp_path / "skills-codex"
    write_skill(shared_root, "alpha", "Alpha skill")
    write_skill(codex_root, "codex-subagent", "Codex-only subagent skill")
    config_path = tmp_path / "shared-ai-config.json"

    write_config(
        config_path,
        skill_roots=[{"path": str(shared_root)}],
        targets={
            "codex": {
                "configPath": str(tmp_path / "codex" / "config.toml"),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "skillRoots": [{"path": str(codex_root)}],
            },
        },
        servers={},
    )

    first = compute_fingerprint(config_path)
    (codex_root / "codex-subagent" / "SKILL.md").write_text(
        "---\nname: codex-subagent\ndescription: Codex-only subagent skill\n---\n\nUpdated.\n",
        encoding="utf-8",
    )
    second = compute_fingerprint(config_path)

    assert first != second


def test_merge_mcp_servers_target_disabled_suppresses_shared_server() -> None:
    shared = (
        McpServerConfig(name="shared", transport="stdio", command="/bin/echo"),
        McpServerConfig(name="override-me", transport="stdio", command="/bin/echo"),
    )
    target = (McpServerConfig(name="override-me", transport="stdio", command="/bin/echo", enabled=False),)
    result = sync_module._merge_mcp_servers(shared, target)
    names = [s.name for s in result]
    assert names == ["shared"]
    assert "override-me" not in names


def test_resolve_skills_uses_repo_local_roots_only(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_skills = repo_root / "skills" / "shared"
    repo_skills.mkdir(parents=True)
    write_skill(repo_skills, "alpha", "Alpha")
    config_path = repo_root / "shared-ai-config.json"
    write_config(
        config_path,
        skill_roots=[
            {
                "path": "${REPO_ROOT}/skills/shared",
            }
        ],
        targets={},
        servers={},
    )

    config = load_sync_config(config_path)
    names = [skill.name for skill in resolve_skills(config.skill_roots, config.include)]

    assert names == ["alpha"]


def test_vendored_serena_manager_defaults_to_repo_local_serena_wrapper(tmp_path: Path) -> None:
    module_path = Path(__file__).resolve().parents[1] / "vendor" / "mcp" / "serena-manager" / "src" / "serena_manager" / "config.py"
    spec = importlib.util.spec_from_file_location("vendored_serena_manager_config", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    manager_root = tmp_path / "repo" / "vendor" / "mcp" / "serena-manager"
    manager_root.mkdir(parents=True)
    config = module.ManagerConfig.default(manager_root)

    assert config.serena_command == str(tmp_path / "repo" / "tools" / "mcp" / "shared" / "serena-agent.sh")
    assert config.serena_args == ("start-mcp-server",)


def test_sync_clients_skips_disabled_servers_for_all_targets(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.parent.mkdir(parents=True)
    opencode_config.write_text("{}\n", encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
            },
            "opencode": {
                "configPath": str(opencode_config),
            },
        },
        servers={
            "enabled-demo": {"type": "stdio", "command": "/bin/echo"},
            "disabled-demo": {"type": "stdio", "command": "/bin/false", "enabled": False},
        },
    )

    result = sync_clients(load_sync_config(config_path), state_path)

    codex_text = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.enabled-demo]" in codex_text
    assert "[mcp_servers.disabled-demo]" not in codex_text

    claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
    assert "enabled-demo" in claude_data["mcpServers"]
    assert "disabled-demo" not in claude_data["mcpServers"]

    opencode_data = json.loads(opencode_config.read_text(encoding="utf-8"))
    assert "enabled-demo" in opencode_data["mcp"]
    assert "disabled-demo" not in opencode_data["mcp"]

    assert result["mcp_servers"] == ["enabled-demo"]
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["codex"]["mcp"] == ["enabled-demo"]
    assert state["claude"]["mcp"] == ["enabled-demo"]
    assert state["opencode"]["mcp"] == ["enabled-demo"]


def test_sync_clients_removes_stale_skill_symlink_without_state(tmp_path: Path) -> None:
    current_root = tmp_path / "skills"
    write_skill(current_root, "alpha", "Alpha")
    write_skill(current_root, "old-skill", "Old")
    config_path = tmp_path / "shared-ai-config.json"
    codex_config = tmp_path / "codex" / "config.toml"
    skills_dir = tmp_path / "codex" / "skills"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(current_root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(skills_dir),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert (skills_dir / "old-skill").is_symlink()

    write_config(
        config_path,
        skill_roots=[{"path": str(current_root), "exclude": ["old-skill"]}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(skills_dir),
            },
        },
        servers={},
    )
    state_path.unlink()

    sync_clients(load_sync_config(config_path), state_path)

    assert not (skills_dir / "old-skill").exists()
    assert (skills_dir / "alpha").is_symlink()


def test_sync_clients_preserves_manual_symlinked_skill_entries(tmp_path: Path) -> None:
    shared_root = tmp_path / "skills"
    manual_root = tmp_path / "manual"
    write_skill(shared_root, "alpha", "Alpha")
    write_skill(manual_root, "custom", "Custom")
    config_path = tmp_path / "shared-ai-config.json"
    claude_config = tmp_path / "claude" / ".claude.json"
    skills_dir = tmp_path / "claude" / "skills"
    state_path = tmp_path / "state" / "sync-state.json"
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text("{}\n", encoding="utf-8")
    skills_dir.mkdir(parents=True)
    (skills_dir / "custom").symlink_to(manual_root / "custom", target_is_directory=True)

    write_config(
        config_path,
        skill_roots=[{"path": str(shared_root)}],
        targets={
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(skills_dir),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert (skills_dir / "custom").is_symlink()
    assert (skills_dir / "alpha").is_symlink()


def test_sync_clients_preserves_opencode_comments_outside_managed_sections(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    opencode_config.parent.mkdir(parents=True)
    opencode_config.write_text(
        '{\n'
        '  // keep schema comment\n'
        '  "$schema": "https://opencode.ai/config.json",\n'
        '  // keep theme comment\n'
        '  "theme": "dark",\n'
        '  "mcp": {\n'
        '    // managed comment can change\n'
        '    "old": { "type": "local", "command": ["/bin/old"], "enabled": true }\n'
        "  }\n"
        '}\n',
        encoding="utf-8",
    )

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "opencode": {
                "configPath": str(opencode_config),
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
    )

    sync_clients(load_sync_config(config_path), state_path)

    synced = opencode_config.read_text(encoding="utf-8")
    assert "// keep schema comment" in synced
    assert "// keep theme comment" in synced
    assert '"theme": "dark"' in synced
    assert '"demo"' in synced
    assert sync_module._load_jsonc(opencode_config)["agent"]["skill-alpha"]["mode"] == "subagent"


def test_watch_loop_recovers_from_sync_errors(monkeypatch, capsys, tmp_path: Path) -> None:
    paths = SyncPaths(
        repo_root=tmp_path,
        config_path=tmp_path / "shared-ai-config.json",
        state_path=tmp_path / "state" / "sync-state.json",
        service_path=tmp_path / "service",
    )
    attempts = {"load": 0, "sleep": 0}

    monkeypatch.setattr(sync_module, "compute_fingerprint", lambda path: "fp")

    def fake_load(path: Path) -> object:
        attempts["load"] += 1
        if attempts["load"] == 1:
            raise SyncError("boom")
        return object()

    monkeypatch.setattr(sync_module, "load_sync_config", fake_load)
    monkeypatch.setattr(sync_module, "sync_clients", lambda config, state_path: {"status": "ok"})

    def fake_sleep(_: float) -> None:
        attempts["sleep"] += 1
        if attempts["sleep"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(sync_module.time, "sleep", fake_sleep)

    with pytest.raises(KeyboardInterrupt):
        watch_loop(paths, 0.0)

    lines = [json.loads(line) for line in capsys.readouterr().out.strip().splitlines()]
    assert lines[0]["error"] == "boom"
    assert lines[0]["watch_fingerprint"] == "fp"
    assert lines[1] == {"status": "ok", "watch_fingerprint": "fp"}


def test_sync_clients_generates_overlay_only_prompt(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    overlay = tmp_path / "codex-overlay.md"
    prompt_path = tmp_path / "codex" / "AGENTS.md"
    codex_config = tmp_path / "codex" / "config.toml"
    overlay.write_text("Overlay only.\n", encoding="utf-8")
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(prompt_path),
                "globalPromptAppendPath": str(overlay),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert prompt_path.read_text(encoding="utf-8") == "Overlay only.\n"


def test_sync_clients_removes_stale_prompt_when_target_is_disabled(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    prompt_path = tmp_path / "codex" / "AGENTS.md"
    codex_config = tmp_path / "codex" / "config.toml"
    shared_prompt.write_text("Shared prompt.\n", encoding="utf-8")
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(prompt_path),
            },
        },
        servers={},
        global_prompt_path=str(shared_prompt),
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert prompt_path.exists()

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert not prompt_path.exists()


def test_sync_clients_removes_stale_prompt_when_sources_are_removed(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    prompt_path = tmp_path / "codex" / "AGENTS.md"
    codex_config = tmp_path / "codex" / "config.toml"
    shared_prompt.write_text("Shared prompt.\n", encoding="utf-8")
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(prompt_path),
            },
        },
        servers={},
        global_prompt_path=str(shared_prompt),
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert prompt_path.exists()

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(prompt_path),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert not prompt_path.exists()


def test_sync_clients_rejects_non_stdio_server_for_codex_target(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
            },
        },
        servers={
            "remote-demo": {"type": "http", "url": "https://example.com/mcp"},
        },
    )

    with pytest.raises(SyncError, match="supports only stdio"):
        sync_clients(load_sync_config(config_path), state_path)


def test_sync_clients_preserves_symlinked_target_files(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    real_config = tmp_path / "real-config.toml"
    symlinked_config = tmp_path / "codex" / "config.toml"
    real_prompt = tmp_path / "real-AGENTS.md"
    symlinked_prompt = tmp_path / "codex" / "AGENTS.md"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    real_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    real_prompt.write_text("old\n", encoding="utf-8")
    shared_prompt.write_text("Shared prompt.\n", encoding="utf-8")
    symlinked_config.parent.mkdir(parents=True)
    symlinked_config.symlink_to(real_config)
    symlinked_prompt.symlink_to(real_prompt)

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(symlinked_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(symlinked_prompt),
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
        global_prompt_path=str(shared_prompt),
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert symlinked_config.is_symlink()
    assert symlinked_prompt.is_symlink()
    assert "[mcp_servers.demo]" in real_config.read_text(encoding="utf-8")
    assert real_prompt.read_text(encoding="utf-8") == "Shared prompt.\n"


def test_sync_clients_removes_symlinked_prompt_backing_file_when_prompt_is_disabled(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    shared_prompt = tmp_path / "shared-global-prompt.md"
    codex_config = tmp_path / "codex" / "config.toml"
    real_prompt = tmp_path / "real-AGENTS.md"
    symlinked_prompt = tmp_path / "codex" / "AGENTS.md"
    shared_prompt.write_text("Shared prompt.\n", encoding="utf-8")
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    real_prompt.write_text("old\n", encoding="utf-8")
    symlinked_prompt.symlink_to(real_prompt)

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
                "globalPromptPath": str(symlinked_prompt),
            },
        },
        servers={},
        global_prompt_path=str(shared_prompt),
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert symlinked_prompt.is_symlink()
    assert real_prompt.read_text(encoding="utf-8") == "Shared prompt.\n"

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(tmp_path / "codex" / "skills"),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert not symlinked_prompt.exists()
    assert not real_prompt.exists()


def test_renderers_reject_stdio_servers_without_command() -> None:
    server = McpServerConfig(name="broken", transport="stdio")

    with pytest.raises(SyncError, match="Missing command"):
        sync_module._render_codex_block((server,))
    with pytest.raises(SyncError, match="Missing command"):
        sync_module._render_claude_server(server)
    with pytest.raises(SyncError, match="Missing command"):
        sync_module._render_opencode_server(server)
    with pytest.raises(SyncError, match="Missing command"):
        sync_module._render_standard_mcp_server(server)


def test_sync_clients_removes_managed_outputs_when_target_is_deleted(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    codex_skills = tmp_path / "codex" / "skills"
    claude_skills = tmp_path / "claude" / "skills"
    pi_skills = tmp_path / "pi" / "skills"
    codex_config.parent.mkdir(parents=True)
    claude_config.parent.mkdir(parents=True)
    opencode_config.parent.mkdir(parents=True)
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.write_text("{}\n", encoding="utf-8")
    pi_settings.write_text('{"packages":["manual","npm:pi-mcp-adapter"],"skills":["/manual/path"]}\n', encoding="utf-8")
    pi_mcp_config.write_text('{"mcpServers":{"manual":{"command":"/bin/true"}}}\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "codex": {
                "configPath": str(codex_config),
                "skillsDir": str(codex_skills),
            },
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(claude_skills),
            },
            "opencode": {
                "configPath": str(opencode_config),
                "agentPrefix": "skill-",
            },
            "pi": {
                "settingsPath": str(pi_settings),
                "mcpConfigPath": str(pi_mcp_config),
                "skillsDir": str(pi_skills),
                "packages": ["npm:pi-mcp-adapter"],
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert (codex_skills / "alpha").is_symlink()
    assert (claude_skills / "alpha").is_symlink()
    assert (pi_skills / "alpha").is_symlink()

    write_config(config_path, skill_roots=[{"path": str(root)}], targets={}, servers={})
    sync_clients(load_sync_config(config_path), state_path)

    assert "[mcp_servers.demo]" not in codex_config.read_text(encoding="utf-8")
    assert not (codex_skills / "alpha").exists()
    claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
    assert claude_data["mcpServers"] == {}
    assert not (claude_skills / "alpha").exists()
    opencode_data = sync_module._load_jsonc(opencode_config)
    assert opencode_data["mcp"] == {}
    assert opencode_data["agent"] == {}
    pi_settings_data = json.loads(pi_settings.read_text(encoding="utf-8"))
    assert pi_settings_data["packages"] == ["manual"]
    assert pi_settings_data["skills"] == ["/manual/path"]
    pi_mcp_data = json.loads(pi_mcp_config.read_text(encoding="utf-8"))
    assert pi_mcp_data["mcpServers"] == {"manual": {"command": "/bin/true"}}
    assert not (pi_skills / "alpha").exists()


def test_sync_clients_preflights_all_targets_before_writing(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    claude_config.parent.mkdir(parents=True)
    opencode_config.parent.mkdir(parents=True)
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.write_text('{\n  bad\n}\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
            },
            "opencode": {
                "configPath": str(opencode_config),
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
    )

    with pytest.raises(SyncError, match="Invalid JSONC object entry"):
        sync_clients(load_sync_config(config_path), state_path)

    assert json.loads(claude_config.read_text(encoding="utf-8")) == {}
    assert not state_path.exists()


def test_sync_clients_cleans_removed_servers_after_previous_failure(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    claude_config.parent.mkdir(parents=True)
    opencode_config.parent.mkdir(parents=True)
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.write_text('{\n  bad\n}\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
            },
            "opencode": {
                "configPath": str(opencode_config),
            },
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
    )

    with pytest.raises(SyncError):
        sync_clients(load_sync_config(config_path), state_path)

    opencode_config.write_text("{}\n", encoding="utf-8")
    write_config(
        config_path,
        skill_roots=[{"path": str(root)}],
        targets={
            "claude": {
                "configPath": str(claude_config),
                "skillsDir": str(tmp_path / "claude" / "skills"),
            },
            "opencode": {
                "configPath": str(opencode_config),
            },
        },
        servers={},
    )

    sync_clients(load_sync_config(config_path), state_path)

    claude_data = json.loads(claude_config.read_text(encoding="utf-8"))
    assert claude_data["mcpServers"] == {}


def test_sync_opencode_accepts_leading_comment_with_braces(tmp_path: Path) -> None:
    config_path = tmp_path / "opencode.jsonc"
    config_path.write_text(
        '// note: { placeholder }\n{\n  "$schema": "https://opencode.ai/config.json"\n}\n',
        encoding="utf-8",
    )

    sync_module.sync_opencode_config(
        config_path,
        (McpServerConfig(name="demo", transport="stdio", command="/bin/echo"),),
        [],
        "skill-",
        [],
        [],
    )

    data = sync_module._load_jsonc(config_path)
    assert "demo" in data["mcp"]


def test_build_global_prompt_skips_empty_base_content(tmp_path: Path) -> None:
    base = tmp_path / "shared-global-prompt.md"
    overlay = tmp_path / "overlay.md"
    base.write_text("", encoding="utf-8")
    overlay.write_text("Overlay only.\n", encoding="utf-8")

    prompt = sync_module.build_global_prompt(base, overlay)

    assert prompt == "Overlay only.\n"


def test_install_service_quotes_paths_with_spaces(tmp_path: Path) -> None:
    repo_root = tmp_path / "space repo"
    repo_root.mkdir()
    cli_path = repo_root / ".venv" / "bin" / "ai-config-sync"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    cli_path.chmod(0o755)
    service_path = tmp_path / "service with space" / "ai-config-sync.service"
    config_path = repo_root / "shared ai config.json"
    paths = SyncPaths(
        repo_root=repo_root,
        config_path=config_path,
        state_path=repo_root / "state" / "sync-state.json",
        service_path=service_path,
    )

    install_service(paths, 2.0)

    text = service_path.read_text(encoding="utf-8")
    assert 'WorkingDirectory=' in text
    assert 'WorkingDirectory="/' not in text
    assert 'ExecStart="' in text
    assert '--config "' in text
    proc = subprocess.run(["systemd-analyze", "verify", str(service_path)], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr


def test_cli_resolves_repo_root_from_console_script_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    script_path = repo_root / ".venv" / "bin" / "ai-config-sync"
    module_path = tmp_path / "site-packages" / "ai_config_sync" / "cli.py"
    script_path.parent.mkdir(parents=True)
    module_path.parent.mkdir(parents=True)
    (repo_root / "shared-ai-config.json").write_text("{}\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text("[project]\nname='ai-config-sync'\n", encoding="utf-8")
    script_path.write_text("", encoding="utf-8")
    module_path.write_text("", encoding="utf-8")

    resolved = cli_module._resolve_repo_root(script_path, module_path, tmp_path)

    assert resolved == repo_root


def test_cli_mcp_add_rolls_back_config_when_sync_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config_path = repo_root / "shared-ai-config.json"
    state_path = repo_root / "state" / "sync-state.json"
    config_path.write_text('{"mcpServers":{},"skillRoots":[],"include":["*"],"targets":{}}\n', encoding="utf-8")
    original = config_path.read_text(encoding="utf-8")

    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(
        cli_module,
        "sync_clients",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(SyncError("boom")),
    )
    monkeypatch.setattr(
        cli_module,
        "default_paths",
        lambda repo_root, config_override=None: SyncPaths(
            repo_root=repo_root,
            config_path=config_override or config_path,
            state_path=state_path,
            service_path=repo_root / "service",
        ),
    )
    monkeypatch.setattr(
        cli_module.sys,
        "argv",
        [
            "ai-config-sync",
            "mcp-add",
            "remote-demo",
            "--transport",
            "http",
            "--url",
            "https://example.com/mcp",
        ],
    )

    with pytest.raises(SystemExit):
        cli_module.main()

    assert config_path.read_text(encoding="utf-8") == original


def test_cli_run_config_update_rolls_back_target_writes_when_sync_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "shared-ai-config.json"
    target_path = tmp_path / "codex" / "config.toml"
    target_path.parent.mkdir(parents=True)
    target_path.write_text('model = "gpt-5"\n', encoding="utf-8")
    skills_dir = tmp_path / "codex" / "skills"
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {},
                "skillRoots": [],
                "include": ["*"],
                "targets": {
                    "codex": {
                        "configPath": str(target_path),
                        "skillsDir": str(skills_dir),
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    original_target = target_path.read_text(encoding="utf-8")

    class FakePaths:
        def __init__(self) -> None:
            self.config_path = config_path
            self.state_path = tmp_path / "state" / "sync-state.json"

    def fake_update(path: Path) -> dict[str, str]:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["mcpServers"]["demo"] = {"type": "stdio", "command": "/bin/echo"}
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
        return {"added": "demo"}

    def fake_sync_clients(config: object, _state_path: Path) -> dict[str, object]:
        assert getattr(config, "codex").config_path == target_path
        target_path.write_text('command = "/bin/echo"\n', encoding="utf-8")
        raise SyncError("boom")

    monkeypatch.setattr(cli_module, "sync_clients", fake_sync_clients)

    with pytest.raises(SyncError, match="boom"):
        cli_module._run_config_update(FakePaths(), fake_update)

    assert '"demo"' not in config_path.read_text(encoding="utf-8")
    assert target_path.read_text(encoding="utf-8") == original_target


def test_cli_run_config_update_rolls_back_pi_package_manifest_when_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "shared-ai-config.json"
    target_path = tmp_path / "codex" / "config.toml"
    pi_settings = tmp_path / "pi" / "settings.json"
    pi_mcp_config = tmp_path / "pi-mcp" / "mcp.json"
    pi_package_json = tmp_path / "pi" / "npm" / "package.json"
    target_path.parent.mkdir(parents=True)
    pi_settings.parent.mkdir(parents=True)
    pi_mcp_config.parent.mkdir(parents=True)
    pi_package_json.parent.mkdir(parents=True)
    target_path.write_text('model = "gpt-5"\n', encoding="utf-8")
    pi_settings.write_text("{}\n", encoding="utf-8")
    pi_mcp_config.write_text("{}\n", encoding="utf-8")
    pi_package_json.write_text(
        json.dumps(
            {
                "name": "pi-extensions",
                "private": True,
                "dependencies": {"pi-mcp-adapter": "^2.10.0"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    original_package_manifest = pi_package_json.read_text(encoding="utf-8")
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {},
                "skillRoots": [],
                "include": ["*"],
                "targets": {
                    "codex": {
                        "configPath": str(target_path),
                        "skillsDir": str(tmp_path / "codex" / "skills"),
                    },
                    "pi": {
                        "settingsPath": str(pi_settings),
                        "mcpConfigPath": str(pi_mcp_config),
                        "skillsDir": str(tmp_path / "pi" / "skills"),
                        "packages": ["npm:pi-mcp-adapter", "npm:pi-subagents"],
                    },
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    class FakePaths:
        def __init__(self) -> None:
            self.config_path = config_path
            self.state_path = tmp_path / "state" / "sync-state.json"

    def fake_update(path: Path) -> dict[str, str]:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["mcpServers"]["demo"] = {"type": "stdio", "command": "/bin/echo"}
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")
        return {"added": "demo"}

    def fake_sync_clients(config: object, _state_path: Path) -> dict[str, object]:
        assert getattr(config, "pi").settings_path == pi_settings
        target_path.write_text('command = "/bin/echo"\n', encoding="utf-8")
        pi_package_json.write_text(
            json.dumps(
                {
                    "name": "pi-extensions",
                    "private": True,
                    "dependencies": {
                        "pi-mcp-adapter": "^2.10.0",
                        "pi-subagents": "^0.30.0",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        raise SyncError("boom")

    monkeypatch.setattr(cli_module, "sync_clients", fake_sync_clients)

    with pytest.raises(SyncError, match="boom"):
        cli_module._run_config_update(FakePaths(), fake_update)

    assert '"demo"' not in config_path.read_text(encoding="utf-8")
    assert target_path.read_text(encoding="utf-8") == 'model = "gpt-5"\n'
    assert pi_package_json.read_text(encoding="utf-8") == original_package_manifest


def test_update_codegraph_pins_exact_version_and_refreshes_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    vendor_dir = repo_root / "vendor" / "mcp" / "codegraph"
    vendor_dir.mkdir(parents=True)
    package_path = vendor_dir / "package.json"
    (vendor_dir / "package-lock.json").write_text("{\"lockfileVersion\":3}\n", encoding="utf-8")
    package_path.write_text(
        json.dumps({"dependencies": {"@colbymchenry/codegraph": "^1.0.1"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path | None]] = []
    toolchain = {"uv": "/toolchain/uv", "npm": "/toolchain/node/bin/npm", "node": "/toolchain/node/bin/node"}

    monkeypatch.setattr(mcp_updates_module, "_latest_npm_version", lambda _name: "1.2.3")
    monkeypatch.setattr(mcp_updates_module, "_prepare_update_toolchain", lambda _repo_root: toolchain)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {"codegraph": {"prepared": True}}})

    def fake_run_command(
        args: list[str],
        cwd: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd))
        assert env_overrides is not None
        assert env_overrides["PATH"].split(":")[0] == str(Path(toolchain["node"]).parent)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mcp_updates_module, "_run_command", fake_run_command)

    result = mcp_updates_module.update_codegraph(repo_root)

    payload = json.loads(package_path.read_text(encoding="utf-8"))
    assert payload["dependencies"]["@colbymchenry/codegraph"] == "1.2.3"
    assert len(calls) == 1
    assert calls[0][0] == [toolchain["npm"], "install", "--package-lock-only", "--ignore-scripts"]
    assert calls[0][1] is not None
    assert calls[0][1].name == "codegraph"
    assert result["name"] == "codegraph"
    assert result["version"] == "1.2.3"
    assert result["previous_version"] == "^1.0.1"


def test_update_serena_agent_refreshes_vendored_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    vendor_dir = repo_root / "vendor" / "mcp" / "serena-agent"
    (vendor_dir / "pylib" / "serena").mkdir(parents=True)
    (vendor_dir / "pylib" / "serena" / "__init__.py").write_text("old\n", encoding="utf-8")
    (vendor_dir / "upstream-dist-info").mkdir(parents=True)
    (vendor_dir / "upstream-dist-info" / "METADATA").write_text("old\n", encoding="utf-8")

    fake_site_packages = tmp_path / "fake-site-packages"
    for package_name in ("serena", "interprompt", "solidlsp"):
        package_dir = fake_site_packages / package_name
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text(f"{package_name}\n", encoding="utf-8")
    dist_info_dir = fake_site_packages / "serena_agent-9.9.9.dist-info"
    dist_info_dir.mkdir()
    (dist_info_dir / "METADATA").write_text("Version: 9.9.9\n", encoding="utf-8")
    (dist_info_dir / "entry_points.txt").write_text("[console_scripts]\n", encoding="utf-8")
    toolchain = {"uv": "/toolchain/uv", "npm": "/toolchain/node/bin/npm", "node": "/toolchain/node/bin/node"}

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        del cwd
        if args[:2] == [toolchain["uv"], "venv"]:
            venv_dir = Path(args[2])
            (venv_dir / "bin").mkdir(parents=True)
            (venv_dir / "bin" / "python").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:4] == [toolchain["uv"], "pip", "freeze", "--python"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="\n".join(
                    [
                        "serena-agent==9.9.9",
                        "interprompt==1.0.0",
                        "solidlsp==2.0.0",
                        "httpx==0.28.1",
                    ]
                )
                + "\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mcp_updates_module, "_latest_pypi_version", lambda _name: "9.9.9")
    monkeypatch.setattr(mcp_updates_module, "_prepare_update_toolchain", lambda _repo_root: toolchain)
    monkeypatch.setattr(mcp_updates_module, "_run_command", fake_run_command)
    monkeypatch.setattr(mcp_updates_module, "_site_packages", lambda _python_bin: fake_site_packages)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {"serena-agent": {"prepared": True}}})

    result = mcp_updates_module.update_serena_agent(repo_root)

    assert (vendor_dir / "pylib" / "serena" / "__init__.py").read_text(encoding="utf-8") == "serena\n"
    assert (vendor_dir / "pylib" / "interprompt" / "__init__.py").read_text(encoding="utf-8") == "interprompt\n"
    assert (vendor_dir / "pylib" / "solidlsp" / "__init__.py").read_text(encoding="utf-8") == "solidlsp\n"
    assert (vendor_dir / "upstream-dist-info" / "METADATA").read_text(encoding="utf-8") == "Version: 9.9.9\n"
    assert (vendor_dir / "requirements.lock").read_text(encoding="utf-8") == "httpx==0.28.1\n"
    assert result["name"] == "serena-agent"
    assert result["version"] == "9.9.9"


def test_update_fetch_refreshes_requirements_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    vendor_dir = repo_root / "vendor" / "mcp" / "fetch"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "requirements.lock").write_text("before\n", encoding="utf-8")
    toolchain = {"uv": "/toolchain/uv", "npm": "/toolchain/node/bin/npm", "node": "/toolchain/node/bin/node"}

    def fake_run_command(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        del cwd
        if args[:2] == [toolchain["uv"], "venv"]:
            venv_dir = Path(args[2])
            (venv_dir / "bin").mkdir(parents=True)
            (venv_dir / "bin" / "python").write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:4] == [toolchain["uv"], "pip", "freeze", "--python"]:
            return subprocess.CompletedProcess(
                args,
                0,
                stdout="httpx==0.28.1\nmcp-server-fetch==2026.6.4\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mcp_updates_module, "_latest_pypi_version", lambda _name: "2026.6.4")
    monkeypatch.setattr(mcp_updates_module, "_prepare_update_toolchain", lambda _repo_root: toolchain)
    monkeypatch.setattr(mcp_updates_module, "_run_command", fake_run_command)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {"fetch": {"prepared": True}}})

    result = mcp_updates_module.update_fetch(repo_root)

    assert (vendor_dir / "requirements.lock").read_text(encoding="utf-8") == "httpx==0.28.1\nmcp-server-fetch==2026.6.4\n"
    assert result["name"] == "fetch"
    assert result["version"] == "2026.6.4"
    assert result["package"] == "mcp-server-fetch"


def test_update_node_repl_linux_updates_pinned_dependencies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    vendor_dir = repo_root / "vendor" / "mcp" / "node-repl-linux"
    vendor_dir.mkdir(parents=True)
    package_path = vendor_dir / "package.json"
    (vendor_dir / "package-lock.json").write_text("{\"lockfileVersion\":3}\n", encoding="utf-8")
    package_path.write_text(
        json.dumps(
            {
                "dependencies": {
                    "@modelcontextprotocol/sdk": "1.29.0",
                    "zod": "4.4.3",
                }
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    calls: list[tuple[list[str], Path | None]] = []
    toolchain = {"uv": "/toolchain/uv", "npm": "/toolchain/node/bin/npm", "node": "/toolchain/node/bin/node"}

    def fake_latest(name: str) -> str:
        return {
            "@modelcontextprotocol/sdk": "1.31.0",
            "zod": "4.5.0",
        }[name]

    def fake_run_command(
        args: list[str],
        cwd: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd))
        assert env_overrides is not None
        assert env_overrides["PATH"].split(":")[0] == str(Path(toolchain["node"]).parent)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(mcp_updates_module, "_latest_npm_version", fake_latest)
    monkeypatch.setattr(mcp_updates_module, "_prepare_update_toolchain", lambda _repo_root: toolchain)
    monkeypatch.setattr(mcp_updates_module, "_run_command", fake_run_command)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {"node-repl-linux": {"prepared": True}}})

    result = mcp_updates_module.update_node_repl_linux(repo_root)

    payload = json.loads(package_path.read_text(encoding="utf-8"))
    assert payload["dependencies"]["@modelcontextprotocol/sdk"] == "1.31.0"
    assert payload["dependencies"]["zod"] == "4.5.0"
    assert len(calls) == 1
    assert calls[0][0] == [toolchain["npm"], "install", "--package-lock-only", "--ignore-scripts"]
    assert calls[0][1] is not None
    assert calls[0][1].name == "node-repl-linux"
    assert result["name"] == "node-repl-linux"
    assert result["dependencies"] == {
        "@modelcontextprotocol/sdk": {"from": "1.29.0", "to": "1.31.0"},
        "zod": {"from": "4.4.3", "to": "4.5.0"},
    }


def test_update_all_mcp_skips_repo_local_serena_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    calls: list[tuple[str, object]] = []
    serena_vendor = repo_root / "vendor" / "mcp" / "serena-agent"
    fetch_vendor = repo_root / "vendor" / "mcp" / "fetch"
    codegraph_vendor = repo_root / "vendor" / "mcp" / "codegraph"
    node_repl_vendor = repo_root / "vendor" / "mcp" / "node-repl-linux"
    (serena_vendor / "pylib").mkdir(parents=True)
    (serena_vendor / "upstream-dist-info").mkdir(parents=True)
    (serena_vendor / "requirements.lock").write_text("lock\n", encoding="utf-8")
    fetch_vendor.mkdir(parents=True)
    (fetch_vendor / "requirements.lock").write_text("lock\n", encoding="utf-8")
    codegraph_vendor.mkdir(parents=True)
    (codegraph_vendor / "package.json").write_text("{}\n", encoding="utf-8")
    (codegraph_vendor / "package-lock.json").write_text("{}\n", encoding="utf-8")
    node_repl_vendor.mkdir(parents=True)
    (node_repl_vendor / "package.json").write_text("{}\n", encoding="utf-8")
    (node_repl_vendor / "package-lock.json").write_text("{}\n", encoding="utf-8")

    def fake_serena_agent(root: Path, version: str | None = None) -> dict[str, object]:
        calls.append(("serena-agent", version))
        return {"name": "serena-agent", "version": version or "latest"}

    def fake_codegraph(root: Path, version: str | None = None) -> dict[str, object]:
        calls.append(("codegraph", version))
        return {"name": "codegraph", "version": version or "latest"}

    def fake_fetch(root: Path, version: str | None = None) -> dict[str, object]:
        calls.append(("fetch", version))
        return {"name": "fetch", "version": version or "latest"}

    def fake_node_repl(
        root: Path,
        sdk_version: str | None = None,
        zod_version: str | None = None,
    ) -> dict[str, object]:
        calls.append(("node-repl-linux", (sdk_version, zod_version)))
        return {"name": "node-repl-linux"}

    monkeypatch.setattr(mcp_updates_module, "update_serena_agent", fake_serena_agent)
    monkeypatch.setattr(mcp_updates_module, "update_fetch", fake_fetch)
    monkeypatch.setattr(mcp_updates_module, "update_codegraph", fake_codegraph)
    monkeypatch.setattr(mcp_updates_module, "update_node_repl_linux", fake_node_repl)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {}})

    result = mcp_updates_module.update_all_mcp(repo_root)

    assert calls == [
        ("serena-agent", None),
        ("fetch", None),
        ("codegraph", None),
        ("node-repl-linux", (None, None)),
    ]
    assert [item["name"] for item in result["updated"]] == [
        "serena-agent",
        "fetch",
        "codegraph",
        "node-repl-linux",
    ]
    assert result["serena_manager"] == {
        "name": "serena-manager",
        "mode": "repo-local-manual",
        "updated": False,
    }


def test_update_all_mcp_rolls_back_when_later_component_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    serena_vendor = repo_root / "vendor" / "mcp" / "serena-agent"
    fetch_vendor = repo_root / "vendor" / "mcp" / "fetch"
    codegraph_vendor = repo_root / "vendor" / "mcp" / "codegraph"
    node_repl_vendor = repo_root / "vendor" / "mcp" / "node-repl-linux"

    (serena_vendor / "pylib").mkdir(parents=True)
    (serena_vendor / "pylib" / "marker.txt").write_text("before-serena\n", encoding="utf-8")
    (serena_vendor / "upstream-dist-info").mkdir(parents=True)
    (serena_vendor / "upstream-dist-info" / "METADATA").write_text("before-metadata\n", encoding="utf-8")
    (serena_vendor / "requirements.lock").write_text("before-lock\n", encoding="utf-8")
    fetch_vendor.mkdir(parents=True)
    (fetch_vendor / "requirements.lock").write_text("before-fetch-lock\n", encoding="utf-8")
    codegraph_vendor.mkdir(parents=True)
    (codegraph_vendor / "package.json").write_text('{"version":"before"}\n', encoding="utf-8")
    (codegraph_vendor / "package-lock.json").write_text('{"lock":"before"}\n', encoding="utf-8")
    node_repl_vendor.mkdir(parents=True)
    (node_repl_vendor / "package.json").write_text('{"version":"before"}\n', encoding="utf-8")
    (node_repl_vendor / "package-lock.json").write_text('{"lock":"before"}\n', encoding="utf-8")

    def fake_serena_agent(root: Path, version: str | None = None) -> dict[str, object]:
        del version
        (root / "vendor" / "mcp" / "serena-agent" / "requirements.lock").write_text("after-serena\n", encoding="utf-8")
        return {"name": "serena-agent"}

    def fake_codegraph(root: Path, version: str | None = None) -> dict[str, object]:
        del version
        (root / "vendor" / "mcp" / "codegraph" / "package.json").write_text('{"version":"after"}\n', encoding="utf-8")
        return {"name": "codegraph"}

    def fake_fetch(root: Path, version: str | None = None) -> dict[str, object]:
        del version
        (root / "vendor" / "mcp" / "fetch" / "requirements.lock").write_text("after-fetch-lock\n", encoding="utf-8")
        return {"name": "fetch"}

    def fake_node_repl(root: Path, sdk_version: str | None = None, zod_version: str | None = None) -> dict[str, object]:
        del root, sdk_version, zod_version
        raise SyncError("boom")

    monkeypatch.setattr(mcp_updates_module, "update_serena_agent", fake_serena_agent)
    monkeypatch.setattr(mcp_updates_module, "update_fetch", fake_fetch)
    monkeypatch.setattr(mcp_updates_module, "update_codegraph", fake_codegraph)
    monkeypatch.setattr(mcp_updates_module, "update_node_repl_linux", fake_node_repl)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {}})

    with pytest.raises(SyncError, match="boom"):
        mcp_updates_module.update_all_mcp(repo_root)

    assert (serena_vendor / "requirements.lock").read_text(encoding="utf-8") == "before-lock\n"
    assert (fetch_vendor / "requirements.lock").read_text(encoding="utf-8") == "before-fetch-lock\n"
    assert (codegraph_vendor / "package.json").read_text(encoding="utf-8") == '{"version":"before"}\n'
    assert (node_repl_vendor / "package.json").read_text(encoding="utf-8") == '{"version":"before"}\n'


def test_cli_mcp_update_all_prints_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(
        cli_module,
        "default_paths",
        lambda repo_root, config_override=None: SyncPaths(
            repo_root=repo_root,
            config_path=config_override or repo_root / "shared-ai-config.json",
            state_path=repo_root / "state" / "sync-state.json",
            service_path=repo_root / "service",
        ),
    )
    monkeypatch.setattr(
        cli_module,
        "update_all_mcp",
        lambda repo_root, **_kwargs: {"updated": [{"name": "codegraph", "version": "1.2.3"}]},
    )
    monkeypatch.setattr(cli_module.sys, "argv", ["ai-config-sync", "mcp-update-all"])

    cli_module.main()

    assert json.loads(capsys.readouterr().out) == {"updated": [{"name": "codegraph", "version": "1.2.3"}]}


def test_cli_mcp_update_fetch_prints_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(cli_module, "update_fetch", lambda repo_root, version=None: {"name": "fetch", "version": version or "2026.6.4"})
    monkeypatch.setattr(cli_module.sys, "argv", ["ai-config-sync", "mcp-update-fetch"])

    cli_module.main()

    assert json.loads(capsys.readouterr().out) == {"name": "fetch", "version": "2026.6.4"}


def test_cli_pi_web_install_prints_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(cli_module, "install_pi_web", lambda version=None: {"version": version or "v1.21.2"})
    monkeypatch.setattr(cli_module.sys, "argv", ["ai-config-sync", "pi-web-install"])

    cli_module.main()

    assert json.loads(capsys.readouterr().out) == {"version": "v1.21.2"}


def test_cli_pi_web_service_start_prints_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(
        cli_module,
        "start_pi_web_service",
        lambda port=8732, hostname="0.0.0.0": {"port": port, "hostname": hostname, "service_active": "active"},
    )
    monkeypatch.setattr(cli_module.sys, "argv", ["ai-config-sync", "pi-web-service-start", "--hostname", "127.0.0.1"])

    cli_module.main()

    assert json.loads(capsys.readouterr().out) == {
        "port": 8732,
        "hostname": "127.0.0.1",
        "service_active": "active",
    }


def test_update_codegraph_keeps_real_manifest_when_npm_refresh_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    vendor_dir = repo_root / "vendor" / "mcp" / "codegraph"
    vendor_dir.mkdir(parents=True)
    package_path = vendor_dir / "package.json"
    lock_path = vendor_dir / "package-lock.json"
    original_package = {"dependencies": {"@colbymchenry/codegraph": "1.0.1"}}
    package_path.write_text(json.dumps(original_package, indent=2) + "\n", encoding="utf-8")
    lock_path.write_text("{\"lockfileVersion\":3}\n", encoding="utf-8")
    toolchain = {"uv": "/toolchain/uv", "npm": "/toolchain/node/bin/npm", "node": "/toolchain/node/bin/node"}

    monkeypatch.setattr(mcp_updates_module, "_latest_npm_version", lambda _name: "1.2.3")
    monkeypatch.setattr(mcp_updates_module, "_prepare_update_toolchain", lambda _repo_root: toolchain)
    monkeypatch.setattr(mcp_updates_module, "preflight_mcp", lambda *_args, **_kwargs: {"runtime": {"codegraph": {"prepared": True}}})

    def fake_run_command(
        args: list[str],
        cwd: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, env_overrides
        raise sync_module.SyncError(f"boom: {' '.join(args)}")

    monkeypatch.setattr(mcp_updates_module, "_run_command", fake_run_command)

    with pytest.raises(SyncError, match="boom"):
        mcp_updates_module.update_codegraph(repo_root)

    assert json.loads(package_path.read_text(encoding="utf-8")) == original_package
    assert lock_path.read_text(encoding="utf-8") == "{\"lockfileVersion\":3}\n"


def test_repo_local_ui_ux_pro_max_assets_are_real_paths() -> None:
    skill_root = Path(__file__).resolve().parents[1] / "skills" / "shared" / "ui-ux-pro-max"

    assert (skill_root / "scripts").is_dir()
    assert (skill_root / "scripts" / "search.py").is_file()
    assert (skill_root / "data").is_dir()


def test_sync_clients_removes_managed_outputs_from_legacy_state_when_target_is_deleted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_home = tmp_path / "home" / ".codex"
    codex_config = codex_home / "config.toml"
    codex_skills = codex_home / "skills-shared"
    codex_config.parent.mkdir(parents=True)
    codex_skills.mkdir(parents=True)
    codex_config.write_text(
        'model = "gpt-5"\n\n[mcp_servers.demo]\ntype = "stdio"\ncommand = "/bin/echo"\n',
        encoding="utf-8",
    )
    (codex_skills / "alpha").symlink_to(root / "alpha", target_is_directory=True)
    monkeypatch.setattr(
        sync_module,
        "_legacy_default_target_paths",
        lambda target_name: {
            "codex": {
                "config_path": codex_config,
                "skills_dirs": (codex_home / "skills-shared", codex_home / "skills"),
            },
            "claude": {
                "config_path": tmp_path / "home" / ".claude.json",
                "skills_dirs": (tmp_path / "home" / ".claude" / "skills",),
            },
            "opencode": {
                "config_path": tmp_path / "home" / ".config" / "opencode" / "opencode.jsonc",
                "skills_dirs": (),
            },
        }[target_name],
    )

    write_config(config_path, skill_roots=[{"path": str(root)}], targets={}, servers={})
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "codex": {
                    "skills": ["alpha"],
                    "mcp": ["demo"],
                },
                "claude": {},
                "opencode": {},
                "last_synced_at": "2026-01-01T00:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    sync_clients(load_sync_config(config_path), state_path)

    assert "[mcp_servers.demo]" not in codex_config.read_text(encoding="utf-8")
    assert not (codex_skills / "alpha").exists()
