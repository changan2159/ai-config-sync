import json
import subprocess
from pathlib import Path

from ai_config_sync.sync import (
    McpServerConfig,
    add_mcp_server,
    default_paths,
    install_service,
    load_sync_config,
    remove_mcp_server,
    resolve_skills,
    start_service,
    stop_service,
    sync_clients,
)


def write_skill(root: Path, name: str, description: str) -> None:
    path = root / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\nUse {name}.\n",
        encoding="utf-8",
    )


def write_config(path: Path, skill_roots: list[dict], targets: dict, servers: dict) -> None:
    path.write_text(
        json.dumps(
            {
                "mcpServers": servers,
                "skillRoots": skill_roots,
                "include": ["*"],
                "targets": targets,
            },
            indent=2,
        )
        + "\n",
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
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text('{"mcpServers":{"manual":{"type":"stdio","command":"/bin/true","args":[],"env":{}}}}\n', encoding="utf-8")
    opencode_config.parent.mkdir(parents=True)
    opencode_config.write_text('{"$schema":"https://opencode.ai/config.json"}\n', encoding="utf-8")

    write_config(
        config_path,
        skill_roots=[
            {"path": str(core_root), "prefix": ""},
            {"path": str(plugin_root), "prefix": "plugin:"},
        ],
        targets={
            "codex": {"configPath": str(codex_config), "skillsDir": str(tmp_path / "codex" / "skills")},
            "claude": {"configPath": str(claude_config), "skillsDir": str(tmp_path / "claude" / "skills")},
            "opencode": {"configPath": str(opencode_config), "agentPrefix": "skill-"},
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo", "args": ["hello"]}},
    )

    result = sync_clients(load_sync_config(config_path), state_path)
    assert result["skills"] == ["alpha", "plugin:beta"]
    assert (tmp_path / "claude" / "skills" / "plugin:beta").is_symlink()
    opencode = json.loads(opencode_config.read_text(encoding="utf-8"))
    assert "skill-plugin:beta" in opencode["agent"]

    write_config(
        config_path,
        skill_roots=[{"path": str(core_root), "prefix": ""}],
        targets={
            "codex": {"configPath": str(codex_config), "skillsDir": str(tmp_path / "codex" / "skills")},
            "claude": {"configPath": str(claude_config), "skillsDir": str(tmp_path / "claude" / "skills")},
            "opencode": {"configPath": str(opencode_config), "agentPrefix": "skill-"},
        },
        servers={"demo2": {"type": "stdio", "command": "/bin/true"}},
    )
    sync_clients(load_sync_config(config_path), state_path)
    assert not (tmp_path / "claude" / "skills" / "plugin:beta").exists()
    text = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.demo]" not in text
    assert "[mcp_servers.demo2]" in text


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
