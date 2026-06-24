import json
import subprocess
from pathlib import Path

import pytest

import ai_config_sync.cli as cli_module
import ai_config_sync.mcp_runtime as runtime_module
from ai_config_sync.sync import SyncError


def write_toolchain_lock(repo_root: Path) -> None:
    (repo_root / "toolchain.lock.json").write_text(
        json.dumps(
            {
                "platform": "linux-x86_64",
                "uv": {
                    "version": "0.11.21",
                    "url": "https://example.com/uv.tar.gz",
                    "archive_root": "uv-x86_64-unknown-linux-gnu",
                },
                "python": {
                    "version": "3.12.11",
                    "distribution": "cpython-3.12.11-linux-x86_64-gnu",
                },
                "node": {
                    "version": "22.22.1",
                    "url": "https://example.com/node.tar.xz",
                    "archive_root": "node-v22.22.1-linux-x64",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_repo_mcp_wrapper_scripts_are_executable() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    wrapper_names = (
        "codegraph.sh",
        "fetch.sh",
        "node-repl-linux.sh",
        "serena-agent.sh",
        "serena-manager.sh",
    )

    for name in wrapper_names:
        wrapper = repo_root / "tools" / "mcp" / "shared" / name
        assert wrapper.is_file()
        assert wrapper.stat().st_mode & 0o111, f"{wrapper} must be executable"


def test_prepare_serena_agent_runtime_uses_repo_local_uv_and_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    paths.uv_bin.parent.mkdir(parents=True)
    paths.uv_bin.write_text("", encoding="utf-8")
    paths.python_bin.parent.mkdir(parents=True)
    paths.python_bin.write_text("", encoding="utf-8")
    vendor_dir = repo_root / "vendor" / "mcp" / "serena-agent"
    (vendor_dir / "pylib" / "serena").mkdir(parents=True)
    (vendor_dir / "requirements.lock").write_text("httpx==0.28.1\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[1] == "venv":
            venv_python = vendor_dir / ".venv" / "bin" / "python"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(runtime_module, "_run_command", fake_run_command)

    result = runtime_module._prepare_serena_agent_runtime(repo_root, paths)

    assert result["prepared"] is True
    assert calls[0][:4] == [str(paths.uv_bin), "venv", "--python", str(paths.python_bin)]
    assert calls[1][:5] == [str(paths.uv_bin), "pip", "install", "--python", str(vendor_dir / ".venv" / "bin" / "python")]


def test_prepare_fetch_runtime_uses_repo_local_uv_and_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    paths.uv_bin.parent.mkdir(parents=True)
    paths.uv_bin.write_text("", encoding="utf-8")
    paths.python_bin.parent.mkdir(parents=True)
    paths.python_bin.write_text("", encoding="utf-8")
    vendor_dir = repo_root / "vendor" / "mcp" / "fetch"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "requirements.lock").write_text("mcp-server-fetch==2026.6.4\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_command(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[1] == "venv":
            fetch_bin = vendor_dir / ".venv" / "bin" / "mcp-server-fetch"
            fetch_bin.parent.mkdir(parents=True)
            fetch_bin.write_text("", encoding="utf-8")
            (vendor_dir / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(runtime_module, "_run_command", fake_run_command)

    result = runtime_module._prepare_fetch_runtime(repo_root, paths)

    assert result["prepared"] is True
    assert calls[0][:4] == [str(paths.uv_bin), "venv", "--python", str(paths.python_bin)]
    assert calls[1][:5] == [str(paths.uv_bin), "pip", "install", "--python", str(vendor_dir / ".venv" / "bin" / "python")]


def test_prepare_fetch_runtime_rejects_missing_requirements_lock(tmp_path: Path) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    paths.uv_bin.parent.mkdir(parents=True)
    paths.uv_bin.write_text("", encoding="utf-8")
    paths.python_bin.parent.mkdir(parents=True)
    paths.python_bin.write_text("", encoding="utf-8")
    (repo_root / "vendor" / "mcp" / "fetch").mkdir(parents=True)

    with pytest.raises(SyncError, match="Missing repo-local fetch lockfile"):
        runtime_module._prepare_fetch_runtime(repo_root, paths)


def test_prepare_fetch_runtime_rejects_missing_entrypoint_after_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    paths.uv_bin.parent.mkdir(parents=True)
    paths.uv_bin.write_text("", encoding="utf-8")
    paths.python_bin.parent.mkdir(parents=True)
    paths.python_bin.write_text("", encoding="utf-8")
    vendor_dir = repo_root / "vendor" / "mcp" / "fetch"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "requirements.lock").write_text("mcp-server-fetch==2026.6.4\n", encoding="utf-8")

    def fake_run_command(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[1] == "venv":
            python_bin = vendor_dir / ".venv" / "bin" / "python"
            python_bin.parent.mkdir(parents=True)
            python_bin.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(runtime_module, "_run_command", fake_run_command)

    with pytest.raises(SyncError, match="Repo-local fetch install did not produce"):
        runtime_module._prepare_fetch_runtime(repo_root, paths)


def test_prepare_codegraph_runtime_uses_repo_local_npm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    paths.npm_bin.parent.mkdir(parents=True)
    paths.npm_bin.write_text("", encoding="utf-8")
    paths.node_bin.write_text("", encoding="utf-8")
    vendor_dir = repo_root / "vendor" / "mcp" / "codegraph"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "package-lock.json").write_text("{}\n", encoding="utf-8")
    calls: list[tuple[list[str], dict[str, str] | None]] = []

    def fake_run_command(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs.get("env_overrides")))
        (vendor_dir / "node_modules" / ".bin").mkdir(parents=True)
        (vendor_dir / "node_modules" / ".bin" / "codegraph").write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(runtime_module, "_run_command", fake_run_command)

    result = runtime_module._prepare_codegraph_runtime(repo_root, paths)

    assert result["prepared"] is True
    assert calls[0][0] == [str(paths.npm_bin), "ci", "--silent"]
    assert calls[0][1] is not None
    assert calls[0][1]["PATH"].split(":")[0] == str(paths.node_bin.parent)


def test_preflight_writes_runtime_env_and_prepares_requested_components(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    paths = runtime_module._toolchain_paths(repo_root)
    prepared: list[str] = []

    def fake_prepare_uv(_paths: runtime_module.ToolchainPaths, _lock: dict[str, object]) -> None:
        paths.uv_bin.parent.mkdir(parents=True)
        paths.uv_bin.write_text("", encoding="utf-8")

    def fake_prepare_python(_paths: runtime_module.ToolchainPaths, _lock: dict[str, object]) -> None:
        paths.python_bin.parent.mkdir(parents=True)
        paths.python_bin.write_text("", encoding="utf-8")

    def fake_prepare_node(_paths: runtime_module.ToolchainPaths, _lock: dict[str, object]) -> None:
        paths.node_bin.parent.mkdir(parents=True)
        paths.node_bin.write_text("", encoding="utf-8")
        paths.npm_bin.write_text("", encoding="utf-8")

    monkeypatch.setattr(runtime_module, "_prepare_uv_toolchain", fake_prepare_uv)
    monkeypatch.setattr(runtime_module, "_prepare_python_toolchain", fake_prepare_python)
    monkeypatch.setattr(runtime_module, "_prepare_node_toolchain", fake_prepare_node)
    monkeypatch.setattr(runtime_module, "_prepare_serena_agent_runtime", lambda *_args: prepared.append("serena-agent") or {"prepared": True})
    monkeypatch.setattr(runtime_module, "_prepare_serena_manager_runtime", lambda *_args: prepared.append("serena-manager") or {"prepared": True})
    monkeypatch.setattr(runtime_module, "_prepare_fetch_runtime", lambda *_args: prepared.append("fetch") or {"prepared": True})
    monkeypatch.setattr(runtime_module, "_prepare_codegraph_runtime", lambda *_args: prepared.append("codegraph") or {"prepared": True})
    monkeypatch.setattr(runtime_module, "_prepare_node_repl_runtime", lambda *_args: prepared.append("node-repl-linux") or {"prepared": True})

    result = runtime_module.preflight_mcp(repo_root, components=["serena-agent", "fetch", "codegraph"])

    assert prepared == ["serena-agent", "fetch", "codegraph"]
    env_text = paths.runtime_env_path.read_text(encoding="utf-8")
    assert "AI_CONFIG_SYNC_TOOLCHAIN_UV" in env_text
    assert "AI_CONFIG_SYNC_TOOLCHAIN_NODE" in env_text
    assert set(result["runtime"]) == {"serena-agent", "fetch", "codegraph"}


def test_cli_mcp_preflight_prints_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(cli_module, "_resolve_repo_root", lambda *_args: repo_root)
    monkeypatch.setattr(cli_module, "preflight_mcp", lambda repo_root: {"toolchain": {"repo_root": str(repo_root)}})
    monkeypatch.setattr(cli_module.sys, "argv", ["ai-config-sync", "mcp-preflight"])

    cli_module.main()

    assert json.loads(capsys.readouterr().out) == {"toolchain": {"repo_root": str(repo_root)}}


def test_preflight_rejects_unsupported_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path
    write_toolchain_lock(repo_root)
    monkeypatch.setattr(runtime_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(runtime_module.platform, "machine", lambda: "arm64")

    with pytest.raises(SyncError, match="Unsupported host platform"):
        runtime_module.preflight_mcp(repo_root, components=[])
