import json
import subprocess
from pathlib import Path

import pytest

import ai_config_sync.cli as cli_module
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
) -> None:
    payload = {
        "mcpServers": servers,
        "skillRoots": skill_roots,
        "include": ["*"],
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
    shared_prompt = tmp_path / "shared-global-prompt.md"
    codex_overlay = tmp_path / "codex-overlay.md"
    claude_overlay = tmp_path / "claude-overlay.md"
    opencode_overlay = tmp_path / "opencode-overlay.md"
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_prompt = tmp_path / "codex" / "AGENTS.md"
    claude_prompt = tmp_path / "claude" / "CLAUDE.md"
    opencode_prompt = tmp_path / "opencode" / "AGENTS.md"
    codex_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.parent.mkdir(parents=True)
    claude_config.write_text('{"mcpServers":{"manual":{"type":"stdio","command":"/bin/true","args":[],"env":{}}}}\n', encoding="utf-8")
    opencode_config.parent.mkdir(parents=True)
    opencode_config.write_text('{"$schema":"https://opencode.ai/config.json"}\n', encoding="utf-8")
    shared_prompt.write_text("Shared global prompt.\n", encoding="utf-8")
    codex_overlay.write_text("Codex overlay.\n", encoding="utf-8")
    claude_overlay.write_text("Claude overlay.\n", encoding="utf-8")
    opencode_overlay.write_text("OpenCode overlay.\n", encoding="utf-8")

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
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo", "args": ["hello"]}},
        global_prompt_path=str(shared_prompt),
    )

    result = sync_clients(load_sync_config(config_path), state_path)
    assert result["skills"] == ["alpha", "plugin:beta"]
    assert (tmp_path / "claude" / "skills" / "plugin:beta").is_symlink()
    assert codex_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nCodex overlay.\n"
    assert claude_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nClaude overlay.\n"
    assert opencode_prompt.read_text(encoding="utf-8") == "Shared global prompt.\n\nOpenCode overlay.\n"
    opencode = json.loads(opencode_config.read_text(encoding="utf-8"))
    assert "skill-plugin:beta" in opencode["agent"]
    assert result["targets"]["codex"]["global_prompt_path"] == str(codex_prompt)
    assert result["targets"]["codex"]["global_prompt_append_path"] == str(codex_overlay)
    assert result["targets"]["claude"]["global_prompt_path"] == str(claude_prompt)
    assert result["targets"]["claude"]["global_prompt_append_path"] == str(claude_overlay)
    assert result["targets"]["opencode"]["global_prompt_path"] == str(opencode_prompt)
    assert result["targets"]["opencode"]["global_prompt_append_path"] == str(opencode_overlay)

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
        },
        servers={"demo2": {"type": "stdio", "command": "/bin/true"}},
        global_prompt_path=str(shared_prompt),
    )
    result = sync_clients(load_sync_config(config_path), state_path)
    assert not (tmp_path / "claude" / "skills" / "plugin:beta").exists()
    text = codex_config.read_text(encoding="utf-8")
    assert "[mcp_servers.demo]" not in text
    assert "[mcp_servers.demo2]" in text


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


def test_sync_clients_removes_managed_outputs_when_target_is_deleted(tmp_path: Path) -> None:
    root = tmp_path / "skills"
    write_skill(root, "alpha", "Alpha")
    config_path = tmp_path / "shared-ai-config.json"
    state_path = tmp_path / "state" / "sync-state.json"
    codex_config = tmp_path / "codex" / "config.toml"
    claude_config = tmp_path / "claude" / ".claude.json"
    opencode_config = tmp_path / "opencode" / "opencode.jsonc"
    codex_skills = tmp_path / "codex" / "skills"
    claude_skills = tmp_path / "claude" / "skills"
    codex_config.parent.mkdir(parents=True)
    claude_config.parent.mkdir(parents=True)
    opencode_config.parent.mkdir(parents=True)
    codex_config.write_text('model = "gpt-5"\n', encoding="utf-8")
    claude_config.write_text("{}\n", encoding="utf-8")
    opencode_config.write_text("{}\n", encoding="utf-8")

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
        },
        servers={"demo": {"type": "stdio", "command": "/bin/echo"}},
    )

    sync_clients(load_sync_config(config_path), state_path)
    assert (codex_skills / "alpha").is_symlink()
    assert (claude_skills / "alpha").is_symlink()

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
