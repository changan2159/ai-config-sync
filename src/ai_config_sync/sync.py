from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MANAGED_BLOCK_BEGIN = "# >>> ai-config-sync managed mcp begin"
MANAGED_BLOCK_END = "# <<< ai-config-sync managed mcp end"


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class McpServerConfig:
    name: str
    transport: str
    command: str | None = None
    args: tuple[str, ...] = ()
    cwd: str | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    tool_timeout_sec: int | None = None
    enabled: bool = True


@dataclass(frozen=True)
class SkillRootConfig:
    path: Path
    prefix: str = ""
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class CodexTargetConfig:
    config_path: Path
    skills_dir: Path


@dataclass(frozen=True)
class ClaudeTargetConfig:
    config_path: Path
    skills_dir: Path


@dataclass(frozen=True)
class OpencodeTargetConfig:
    config_path: Path
    agent_prefix: str = "skill-"


@dataclass(frozen=True)
class SyncConfig:
    mcp_servers: tuple[McpServerConfig, ...]
    skill_roots: tuple[SkillRootConfig, ...]
    include: tuple[str, ...]
    codex: CodexTargetConfig | None
    claude: ClaudeTargetConfig | None
    opencode: OpencodeTargetConfig | None


@dataclass(frozen=True)
class ResolvedSkill:
    name: str
    source_dir: Path
    skill_file: Path
    prompt: str
    description: str


@dataclass(frozen=True)
class SyncPaths:
    repo_root: Path
    config_path: Path
    state_path: Path
    service_path: Path
    service_name: str = "ai-config-sync.service"


def default_paths(repo_root: Path, config_path: Path | None = None) -> SyncPaths:
    resolved_config = config_path.expanduser() if config_path else repo_root / "shared-ai-config.json"
    return SyncPaths(
        repo_root=repo_root,
        config_path=resolved_config,
        state_path=repo_root / "state" / "sync-state.json",
        service_path=Path.home() / ".config" / "systemd" / "user" / "ai-config-sync.service",
    )


def load_sync_config(path: Path) -> SyncConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    roots = tuple(
        SkillRootConfig(
            path=Path(item["path"]).expanduser(),
            prefix=str(item.get("prefix", "")),
            exclude=tuple(item.get("exclude", [])),
        )
        for item in data.get("skillRoots", [])
    )
    mcp_servers = tuple(_parse_mcp_server(name, item) for name, item in data.get("mcpServers", {}).items())
    targets = data.get("targets", {})
    codex = CodexTargetConfig(
        config_path=Path(targets["codex"]["configPath"]).expanduser(),
        skills_dir=Path(targets["codex"]["skillsDir"]).expanduser(),
    ) if "codex" in targets else None
    claude = ClaudeTargetConfig(
        config_path=Path(targets["claude"]["configPath"]).expanduser(),
        skills_dir=Path(targets["claude"]["skillsDir"]).expanduser(),
    ) if "claude" in targets else None
    opencode = OpencodeTargetConfig(
        config_path=Path(targets["opencode"]["configPath"]).expanduser(),
        agent_prefix=str(targets["opencode"].get("agentPrefix", "skill-")),
    ) if "opencode" in targets else None
    return SyncConfig(
        mcp_servers=mcp_servers,
        skill_roots=roots,
        include=tuple(data.get("include", ["*"])),
        codex=codex,
        claude=claude,
        opencode=opencode,
    )


def sync_clients(config: SyncConfig, state_path: Path) -> dict[str, Any]:
    previous = _load_state(state_path)
    previous_claude_mcp = previous.get("claude", {}).get("mcp", [])
    previous_codex_mcp = previous.get("codex", {}).get("mcp", [])
    previous_opencode_mcp = previous.get("opencode", {}).get("mcp", [])
    previous_codex_skills = previous.get("codex", {}).get("skills", [])
    previous_claude_skills = previous.get("claude", {}).get("skills", [])
    previous_opencode_agents = previous.get("opencode", {}).get("agents", [])

    skills = resolve_skills(config.skill_roots, config.include)

    result: dict[str, Any] = {
        "mcp_servers": [server.name for server in config.mcp_servers],
        "skills": [skill.name for skill in skills],
        "targets": {},
    }

    if config.codex:
        sync_codex_config(config.codex.config_path, config.mcp_servers, previous_codex_mcp)
        result["targets"]["codex"] = {
            "config_path": str(config.codex.config_path),
            "skills": sync_skill_links(config.codex.skills_dir, skills, previous_codex_skills),
        }

    if config.claude:
        sync_claude_config(config.claude.config_path, config.mcp_servers, previous_claude_mcp)
        result["targets"]["claude"] = {
            "config_path": str(config.claude.config_path),
            "skills": sync_skill_links(config.claude.skills_dir, skills, previous_claude_skills),
        }

    if config.opencode:
        sync_opencode_config(
            config.opencode.config_path,
            config.mcp_servers,
            skills,
            config.opencode.agent_prefix,
            previous_opencode_mcp,
            previous_opencode_agents,
        )
        result["targets"]["opencode"] = {
            "config_path": str(config.opencode.config_path),
            "agents": [f"{config.opencode.agent_prefix}{skill.name}" for skill in skills],
        }

    state = {
        "codex": {
            "mcp": [server.name for server in config.mcp_servers],
            "skills": [skill.name for skill in skills],
        } if config.codex else {},
        "claude": {
            "mcp": [server.name for server in config.mcp_servers],
            "skills": [skill.name for skill in skills],
        } if config.claude else {},
        "opencode": {
            "mcp": [server.name for server in config.mcp_servers],
            "agents": [f"{config.opencode.agent_prefix}{skill.name}" for skill in skills],
        } if config.opencode else {},
        "last_synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def watch_loop(paths: SyncPaths, interval_seconds: float) -> None:
    last_fingerprint: str | None = None
    while True:
        fingerprint = compute_fingerprint(paths.config_path)
        if fingerprint != last_fingerprint:
            config = load_sync_config(paths.config_path)
            result = sync_clients(config, paths.state_path)
            result["watch_fingerprint"] = fingerprint
            print(json.dumps(result, ensure_ascii=False), flush=True)
            last_fingerprint = fingerprint
        time.sleep(interval_seconds)


def compute_fingerprint(config_path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(config_path.read_bytes())
    config = load_sync_config(config_path)
    for skill in resolve_skills(config.skill_roots, config.include):
        digest.update(skill.skill_file.read_bytes())
    return digest.hexdigest()


def resolve_skills(roots: tuple[SkillRootConfig, ...], include: tuple[str, ...]) -> list[ResolvedSkill]:
    discovered = discover_skills(roots)
    if not include or include == ("*",):
        names = sorted(discovered.keys())
    else:
        names = list(include)
    resolved: list[ResolvedSkill] = []
    for name in names:
        source_dir = discovered.get(name)
        if source_dir is None:
            raise SyncError(f"Skill '{name}' was not found in configured roots")
        skill_file = source_dir / "SKILL.md"
        prompt = skill_file.read_text(encoding="utf-8")
        resolved.append(
            ResolvedSkill(
                name=name,
                source_dir=source_dir,
                skill_file=skill_file,
                prompt=prompt,
                description=_extract_description(prompt) or f"Shared skill mirrored from {name}",
            )
        )
    return resolved


def discover_skills(roots: tuple[SkillRootConfig, ...]) -> dict[str, Path]:
    discovered: dict[str, Path] = {}
    for root in roots:
        if not root.path.exists():
            continue
        for child in sorted(root.path.iterdir()):
            if child.name in root.exclude:
                continue
            if not child.is_dir():
                continue
            if not (child / "SKILL.md").is_file():
                continue
            name = f"{root.prefix}{child.name}"
            discovered[name] = child
    return discovered


def sync_skill_links(target_dir: Path, skills: list[ResolvedSkill], previous_names: list[str]) -> dict[str, list[str]]:
    target_dir.mkdir(parents=True, exist_ok=True)
    current = {skill.name for skill in skills}
    removed: list[str] = []
    linked: list[str] = []
    for name in previous_names:
        if name in current:
            continue
        path = target_dir / name
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
            removed.append(name)
    for skill in skills:
        path = target_dir / skill.name
        if path.is_symlink() and path.resolve() == skill.source_dir.resolve():
            linked.append(skill.name)
            continue
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                path.unlink()
            else:
                raise SyncError(f"Refusing to overwrite non-symlink skill path: {path}")
        path.symlink_to(skill.source_dir, target_is_directory=True)
        linked.append(skill.name)
    return {"linked": linked, "removed": removed}


def sync_codex_config(config_path: Path, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> None:
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    cleaned = _strip_managed_block(original)
    for name in previous_names:
        cleaned = _strip_named_codex_section(cleaned, name)
    managed = _render_codex_block(servers)
    payload = f"{cleaned.rstrip()}\n\n{managed}\n" if cleaned.strip() else f"{managed}\n"
    config_path.write_text(payload, encoding="utf-8")


def sync_claude_config(config_path: Path, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> None:
    data = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    current = dict(data.get("mcpServers", {}))
    for name in previous_names:
        current.pop(name, None)
    for server in servers:
        current[server.name] = _render_claude_server(server)
    data["mcpServers"] = current
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sync_opencode_config(
    config_path: Path,
    servers: tuple[McpServerConfig, ...],
    skills: list[ResolvedSkill],
    agent_prefix: str,
    previous_mcp_names: list[str],
    previous_agent_names: list[str],
) -> None:
    data = _load_jsonc(config_path)
    current_mcp = dict(data.get("mcp", {}))
    for name in previous_mcp_names:
        current_mcp.pop(name, None)
    for server in servers:
        current_mcp[server.name] = _render_opencode_server(server)
    data["mcp"] = current_mcp

    current_agents = dict(data.get("agent", {}))
    for name in previous_agent_names:
        current_agents.pop(name, None)
    for skill in skills:
        current_agents[f"{agent_prefix}{skill.name}"] = {
            "description": skill.description,
            "mode": "subagent",
            "prompt": skill.prompt,
        }
    data["agent"] = current_agents

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_mcp_server(config_path: Path, server: McpServerConfig) -> dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    current = dict(data.get("mcpServers", {}))
    current[server.name] = _render_source_server(server)
    data["mcpServers"] = current
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"added": server.name}


def remove_mcp_server(config_path: Path, name: str) -> dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    current = dict(data.get("mcpServers", {}))
    existed = name in current
    current.pop(name, None)
    data["mcpServers"] = current
    config_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"removed": existed, "name": name}


def install_service(paths: SyncPaths, interval_seconds: float) -> dict[str, Any]:
    paths.service_path.parent.mkdir(parents=True, exist_ok=True)
    cli_path = paths.repo_root / ".venv" / "bin" / "ai-config-sync"
    content = (
        "[Unit]\n"
        "Description=AI config sync watch\n"
        "After=default.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={paths.repo_root}\n"
        f"ExecStart={cli_path} sync-watch --config {paths.config_path} --interval {interval_seconds}\n"
        "Restart=always\n"
        "RestartSec=2\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    paths.service_path.write_text(content, encoding="utf-8")
    return {"installed": True, "service_path": str(paths.service_path)}


def service_status(paths: SyncPaths) -> dict[str, Any]:
    active = _run_systemctl("--user", "is-active", paths.service_name, check=False)
    enabled = _run_systemctl("--user", "is-enabled", paths.service_name, check=False)
    return {
        "installed": paths.service_path.exists(),
        "service_path": str(paths.service_path),
        "active": active["stdout"].strip(),
        "active_exit_code": active["returncode"],
        "enabled": enabled["stdout"].strip(),
        "enabled_exit_code": enabled["returncode"],
    }


def start_service(paths: SyncPaths, interval_seconds: float) -> dict[str, Any]:
    install_service(paths, interval_seconds)
    _run_systemctl("--user", "daemon-reload")
    _run_systemctl("--user", "enable", "--now", paths.service_name)
    return service_status(paths)


def stop_service(paths: SyncPaths) -> dict[str, Any]:
    _run_systemctl("--user", "disable", "--now", paths.service_name, check=False)
    return service_status(paths)


def _parse_mcp_server(name: str, item: dict[str, Any]) -> McpServerConfig:
    return McpServerConfig(
        name=name,
        transport=str(item.get("type", "stdio")),
        command=item.get("command"),
        args=tuple(item.get("args", [])),
        cwd=item.get("cwd"),
        env={str(k): str(v) for k, v in item.get("env", {}).items()} or None,
        url=item.get("url"),
        headers={str(k): str(v) for k, v in item.get("headers", {}).items()} or None,
        tool_timeout_sec=int(item["toolTimeoutSec"]) if item.get("toolTimeoutSec") is not None else None,
        enabled=bool(item.get("enabled", True)),
    )


def _render_source_server(server: McpServerConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": server.transport, "enabled": server.enabled}
    if server.transport == "stdio":
        if not server.command:
            raise SyncError(f"Missing command for stdio server '{server.name}'")
        payload["command"] = server.command
        if server.args:
            payload["args"] = list(server.args)
        if server.cwd:
            payload["cwd"] = server.cwd
        if server.env:
            payload["env"] = server.env
        if server.tool_timeout_sec is not None:
            payload["toolTimeoutSec"] = server.tool_timeout_sec
        return payload
    if not server.url:
        raise SyncError(f"Missing url for remote server '{server.name}'")
    payload["url"] = server.url
    if server.headers:
        payload["headers"] = server.headers
    if server.tool_timeout_sec is not None:
        payload["toolTimeoutSec"] = server.tool_timeout_sec
    return payload


def _render_codex_block(servers: tuple[McpServerConfig, ...]) -> str:
    lines = [MANAGED_BLOCK_BEGIN]
    for server in servers:
        if server.transport != "stdio":
            raise SyncError(f"Codex sync currently supports only stdio MCP servers: {server.name}")
        lines.extend(
            [
                f"[mcp_servers.{server.name}]",
                'type = "stdio"',
                f'command = "{_escape(server.command or "")}"',
            ]
        )
        if server.args:
            args = ", ".join(f'"{_escape(arg)}"' for arg in server.args)
            lines.append(f"args = [{args}]")
        if server.cwd:
            lines.append(f'cwd = "{_escape(server.cwd)}"')
        if server.tool_timeout_sec is not None:
            lines.append(f"tool_timeout_sec = {server.tool_timeout_sec}")
        if server.env:
            env = ", ".join(f'{key} = "{_escape(value)}"' for key, value in server.env.items())
            lines.append(f"env = {{ {env} }}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
    lines.append(MANAGED_BLOCK_END)
    return "\n".join(lines)


def _render_claude_server(server: McpServerConfig) -> dict[str, Any]:
    if server.transport == "stdio":
        return {
            "type": "stdio",
            "command": server.command,
            "args": list(server.args),
            "env": server.env or {},
        }
    payload = {"type": server.transport, "url": server.url}
    if server.headers:
        payload["headers"] = server.headers
    return payload


def _render_opencode_server(server: McpServerConfig) -> dict[str, Any]:
    if server.transport == "stdio":
        payload: dict[str, Any] = {
            "type": "local",
            "command": [server.command, *server.args],
            "enabled": server.enabled,
        }
        if server.env:
            payload["environment"] = server.env
        if server.tool_timeout_sec is not None:
            payload["timeout"] = server.tool_timeout_sec * 1000
        return payload
    payload = {"type": "remote", "url": server.url, "enabled": server.enabled}
    if server.headers:
        payload["headers"] = server.headers
    if server.tool_timeout_sec is not None:
        payload["timeout"] = server.tool_timeout_sec * 1000
    return payload


def _strip_managed_block(content: str) -> str:
    pattern = re.compile(rf"\n?{re.escape(MANAGED_BLOCK_BEGIN)}.*?{re.escape(MANAGED_BLOCK_END)}\n?", re.DOTALL)
    return re.sub(pattern, "\n", content).strip("\n")


def _strip_named_codex_section(content: str, name: str) -> str:
    header = f"[mcp_servers.{name}]"
    lines = content.splitlines()
    result: list[str] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() == header:
            index += 1
            while index < len(lines) and not (lines[index].startswith("[") and lines[index].endswith("]")):
                index += 1
            continue
        result.append(lines[index])
        index += 1
    return "\n".join(result).strip("\n")


def _load_jsonc(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    return json.loads(_strip_jsonc_comments(text)) if text.strip() else {}


def _strip_jsonc_comments(text: str) -> str:
    result: list[str] = []
    in_string = False
    string_char = ""
    in_line_comment = False
    in_block_comment = False
    escaped = False
    index = 0
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                result.append(char)
            index += 1
            continue
        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_char:
                in_string = False
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = True
            string_char = char
            result.append(char)
            index += 1
            continue
        if char == "/" and next_char == "/":
            in_line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            in_block_comment = True
            index += 2
            continue
        result.append(char)
        index += 1
    return "".join(result)


def _extract_description(prompt: str) -> str | None:
    if not prompt.startswith("---\n"):
        return None
    header, _, _ = prompt.partition("\n---\n")
    for line in header.splitlines():
        match = re.match(r'description:\s*"?(.*?)"?$', line.strip())
        if match:
            return match.group(1).strip()
    return None


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_systemctl(*args: str, check: bool = True) -> dict[str, Any]:
    proc = subprocess.run(("systemctl", *args), capture_output=True, text=True, encoding="utf-8", check=False)
    if check and proc.returncode != 0:
        raise SyncError(proc.stderr.strip() or proc.stdout.strip() or f"systemctl failed: {' '.join(args)}")
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
