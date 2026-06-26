"""FastAPI dashboard for managing codex / claude / opencode / pi runtimes."""
from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
SETTINGS_PATH = Path.home() / ".config" / "ai-config-sync" / "web-settings.json"

TOOLS: dict[str, dict[str, Any]] = {
    "paseo":    {"label": "Paseo",    "npm": "@getpaseo/cli",               "cmd": "paseo",   "script": "scripts/paseo/update-paseo.sh",        "color": "#c27aff"},
    "codex":    {"label": "Codex",    "npm": "@openai/codex",               "cmd": "codex",    "script": "scripts/codex/update-codex.sh",       "color": "#3fb950"},
    "claude":   {"label": "Claude",   "npm": "@anthropic-ai/claude-code",    "cmd": "claude",   "script": "scripts/claude/update-claude.sh",      "color": "#58a6ff"},
    "opencode": {"label": "OpenCode", "github": "anomalyco/opencode",        "cmd": "opencode", "script": "scripts/opencode/update-opencode.sh",  "color": "#f78166"},
    "pi":       {"label": "Pi",       "npm": "@earendil-works/pi-coding-agent", "cmd": "pi",   "script": "scripts/pi/update-pi.sh",              "color": "#a371f7"},
}

TOOL_PROCS: dict[str, list[str]] = {
    "codex":    ["codex"],
    "claude":   ["claude", "claude-code"],
    "opencode": ["opencode"],
    "pi":       ["pi"],
    "paseo":    ["paseo"],
}

MCP_COMPONENTS: dict[str, dict[str, Any]] = {
    "fetch": {
        "label": "Fetch",
        "kind": "pypi",
        "package": "mcp-server-fetch",
        "wrapper_path": "tools/mcp/shared/fetch.sh",
        "install_root": "vendor/mcp/fetch",
        "version_path": "vendor/mcp/fetch/requirements.lock",
        "update_script": "scripts/mcp/update-fetch.sh",
    },
    "serena": {
        "label": "Serena Agent",
        "kind": "pypi",
        "package": "serena-agent",
        "wrapper_path": "tools/mcp/shared/serena-manager.sh",
        "install_root": "vendor/mcp/serena-agent",
        "manager_root": "vendor/mcp/serena-manager",
        "version_path": "vendor/mcp/serena-agent/upstream-dist-info/METADATA",
        "update_script": "scripts/mcp/update-serena-agent.sh",
        "manager_label": "Serena Manager",
    },
    "codegraph": {
        "label": "CodeGraph",
        "kind": "npm",
        "package": "@colbymchenry/codegraph",
        "wrapper_path": "tools/mcp/shared/codegraph.sh",
        "install_root": "vendor/mcp/codegraph",
        "version_path": "vendor/mcp/codegraph/package.json",
        "update_script": "scripts/mcp/update-codegraph.sh",
    },
    "node_repl": {
        "label": "Node REPL",
        "kind": "npm-deps",
        "package": "@modelcontextprotocol/sdk + zod",
        "wrapper_path": "tools/mcp/shared/node-repl-linux.sh",
        "install_root": "vendor/mcp/node-repl-linux",
        "version_path": "vendor/mcp/node-repl-linux/package.json",
        "update_script": "scripts/mcp/update-node-repl-linux.sh",
    },
}

# ─── settings ─────────────────────────────────────────────────────────────────

def _load_settings() -> dict[str, Any]:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_settings(data: dict[str, Any]) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    SETTINGS_PATH.chmod(0o600)


# ─── job store ────────────────────────────────────────────────────────────────

@dataclass
class Job:
    id: str
    label: str
    status: str = "running"
    lines: list[str] = field(default_factory=list)
    q: queue.Queue = field(default_factory=queue.Queue)

_jobs: dict[str, Job] = {}
_NPM_LATEST_CACHE: dict[str, tuple[float, str | None]] = {}


def _run_job(job: Job, fn: Any) -> None:
    def _emit(line: str) -> None:
        job.lines.append(line)
        job.q.put(line)
    try:
        fn(_emit)
        job.status = "done"
    except Exception as exc:
        job.status = "error"
        _emit(f"ERROR: {exc}")
    finally:
        job.q.put(None)


def _spawn_job(label: str, fn: Any) -> Job:
    job = Job(id=str(uuid.uuid4()), label=label)
    _jobs[job.id] = job
    threading.Thread(target=_run_job, args=(job, fn), daemon=True).start()
    return job


# ─── helpers ──────────────────────────────────────────────────────────────────

def _run(args: list[str], *, cwd: Path | None = None, timeout: int = 30,
         input: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", timeout=timeout, input=input)


def _npm_latest(package: str) -> str | None:
    npm = shutil.which("npm")
    if not npm:
        return None
    try:
        r = _run([npm, "view", package, "version"], timeout=15)
        v = r.stdout.strip()
        return v if r.returncode == 0 and v else None
    except Exception:
        return None


def _cached_npm_latest(package: str, *, ttl_seconds: int = 1800) -> str | None:
    now = time.monotonic()
    cached = _NPM_LATEST_CACHE.get(package)
    if cached and now - cached[0] < ttl_seconds:
        return cached[1]
    latest = _npm_latest(package)
    _NPM_LATEST_CACHE[package] = (now, latest)
    return latest


def _github_latest(repo: str) -> str | None:
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases/latest",
            headers={"Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            tag = json.loads(resp.read()).get("tag_name", "").lstrip("v")
        return tag or None
    except Exception:
        return _github_latest_redirect(f"https://github.com/{repo}/releases/latest")


def _github_latest_redirect(url: str) -> str | None:
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "ai-config-sync"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.geturl()
        match = re.search(r"/releases/tag/v?([^/]+)$", final_url)
        return match.group(1) if match else None
    except Exception:
        return None


def _cmd_version(cmd: str) -> str | None:
    path = shutil.which(cmd)
    if not path:
        return None
    try:
        r = _run([path, "--version"], timeout=10)
        out = (r.stdout or r.stderr).strip()
        m = re.search(r"(\d+\.\d+[\.\d]*)", out)
        return m.group(1) if m else (out[:30] or None)
    except Exception:
        return None


def _service_status(name: str) -> str:
    try:
        return _run(["systemctl", "is-active", name], timeout=5).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _which_path(cmd: str) -> Path | None:
    resolved = shutil.which(cmd)
    return Path(resolved).expanduser() if resolved else None


def _find_paseo_launcher() -> Path | None:
    launcher = _which_path("paseo")
    if launcher is not None:
        return launcher
    home = Path.home()
    candidates = [
        home / ".local" / "bin" / "paseo",
        home / ".local" / "lib" / "node_modules" / "@getpaseo" / "cli" / "bin" / "paseo",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _safe_resolve(path: Path | None) -> Path | None:
    if path is None:
        return None
    try:
        return path.expanduser().resolve()
    except OSError:
        return path.expanduser()


def _command_location(cmd: str) -> dict[str, str | None]:
    launcher = _which_path(cmd)
    resolved = _safe_resolve(launcher)
    install_root: Path | None = None
    if resolved is not None and resolved.is_dir():
        install_root = resolved
    elif launcher is not None and launcher.parent.name == "bin":
        install_root = launcher.parent.parent
    elif resolved is not None:
        install_root = resolved.parent
    return {
        "launcher_path": str(launcher) if launcher else None,
        "resolved_path": str(resolved) if resolved else None,
        "install_root": str(install_root) if install_root else None,
    }


def _systemctl_exec_argv(service_name: str) -> list[str]:
    try:
        result = _run(["systemctl", "show", service_name, "-p", "ExecStart", "--value"], timeout=10)
    except Exception:
        return []
    payload = result.stdout.strip()
    match = re.search(r"argv\[\]=(.*?)(?:\s+;\s|$)", payload)
    if not match:
        return []
    try:
        return shlex.split(match.group(1).strip())
    except ValueError:
        return []


def _argv_option(args: list[str], *names: str) -> str | None:
    for index, arg in enumerate(args):
        if arg in names and index + 1 < len(args):
            return args[index + 1]
        for name in names:
            prefix = f"{name}="
            if arg.startswith(prefix):
                return arg[len(prefix):]
    return None


def _build_local_web_url(hostname: str | None, port: str | int | None) -> str | None:
    if port in (None, "", 0):
        return None
    host = (hostname or "").strip() or "127.0.0.1"
    if host in {"0.0.0.0", "::", "[::]"}:
        host = "127.0.0.1"
    return f"http://{host}:{port}"


def _service_web_details(service_name: str, *, host_flags: tuple[str, ...], port_flags: tuple[str, ...]) -> dict[str, Any]:
    argv = _systemctl_exec_argv(service_name)
    hostname = _argv_option(argv, *host_flags)
    port_text = _argv_option(argv, *port_flags)
    port: int | None = None
    if port_text:
        try:
            port = int(port_text)
        except ValueError:
            port = None
    return {
        "argv": argv,
        "host": hostname,
        "port": port,
        "url": _build_local_web_url(hostname, port),
    }


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _paseo_agent_project_root(agent_id: str | None) -> str | None:
    if not agent_id:
        return None
    agents_root = Path.home() / ".paseo" / "agents"
    try:
        matches = sorted(agents_root.glob(f"**/{agent_id}.json"))
    except OSError:
        return None
    for match in matches:
        payload = _read_json_file(match)
        cwd = payload.get("cwd")
        if isinstance(cwd, str) and cwd.strip():
            return _normalize_project_root(cwd)
        metadata = payload.get("persistence", {}).get("metadata", {}) if isinstance(payload.get("persistence"), dict) else {}
        meta_cwd = metadata.get("cwd") if isinstance(metadata, dict) else None
        if isinstance(meta_cwd, str) and meta_cwd.strip():
            return _normalize_project_root(meta_cwd)
    return None


def _read_metadata_version(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(r"^Version:\s*(.+)$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def _read_requirements_version(path: Path, package_name: str) -> str | None:
    if not path.exists():
        return None
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{package_name}=="):
                return line.split("==", 1)[1].strip() or None
    except OSError:
        return None
    return None


def _read_dependency_version(path: Path, dependency_name: str) -> str | None:
    payload = _read_json_file(path)
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, dict):
        return None
    version = dependencies.get(dependency_name)
    return version.strip() if isinstance(version, str) and version.strip() else None


def _latest_pypi_version(package_name: str) -> str | None:
    try:
        from ai_config_sync.mcp_updates import _latest_pypi_version as _resolve_latest_pypi_version
        return _resolve_latest_pypi_version(package_name)
    except Exception:
        return None


def _latest_npm_version(package_name: str) -> str | None:
    try:
        from ai_config_sync.mcp_updates import _latest_npm_version as _resolve_latest_npm_version
        return _resolve_latest_npm_version(package_name)
    except Exception:
        return None


def _format_dependency_versions(values: dict[str, str | None]) -> str | None:
    parts = [f"{name} {version}" for name, version in values.items() if version]
    return " / ".join(parts) if parts else None


def _get_mcp_component_details(name: str) -> dict[str, Any]:
    meta = MCP_COMPONENTS.get(name)
    if meta is None:
        return {
            "managed": False,
            "component_label": name,
            "current_version": None,
            "latest_version": None,
            "has_update": False,
            "install_root": None,
            "wrapper_path": None,
            "update_script": None,
            "manager_root": None,
        }

    install_root = REPO_ROOT / meta["install_root"]
    wrapper_path = REPO_ROOT / meta["wrapper_path"]
    update_script = REPO_ROOT / meta["update_script"]
    manager_root = REPO_ROOT / meta["manager_root"] if meta.get("manager_root") else None
    current_version: str | None = None
    latest_version: str | None = None
    version_details: dict[str, str | None] | None = None

    if meta["kind"] == "pypi":
        package_name = str(meta["package"])
        version_path = REPO_ROOT / meta["version_path"]
        if name == "serena":
            current_version = _read_metadata_version(version_path)
        else:
            current_version = _read_requirements_version(version_path, package_name)
        latest_version = _latest_pypi_version(package_name)
    elif meta["kind"] == "npm":
        package_name = str(meta["package"])
        version_path = REPO_ROOT / meta["version_path"]
        current_version = _read_dependency_version(version_path, package_name)
        latest_version = _latest_npm_version(package_name)
    elif meta["kind"] == "npm-deps":
        version_path = REPO_ROOT / meta["version_path"]
        version_details = {
            "sdk": _read_dependency_version(version_path, "@modelcontextprotocol/sdk"),
            "zod": _read_dependency_version(version_path, "zod"),
        }
        latest_details = {
            "sdk": _latest_npm_version("@modelcontextprotocol/sdk"),
            "zod": _latest_npm_version("zod"),
        }
        current_version = _format_dependency_versions(version_details)
        latest_version = _format_dependency_versions(latest_details)
        version_details = {
            "sdk": version_details["sdk"],
            "zod": version_details["zod"],
            "latest_sdk": latest_details["sdk"],
            "latest_zod": latest_details["zod"],
        }

    return {
        "managed": True,
        "component_label": meta["label"],
        "package_name": meta["package"],
        "current_version": current_version,
        "latest_version": latest_version,
        "has_update": bool(current_version and latest_version and current_version != latest_version),
        "install_root": str(install_root),
        "wrapper_path": str(wrapper_path),
        "update_script": str(update_script),
        "manager_root": str(manager_root) if manager_root else None,
        "manager_label": meta.get("manager_label"),
        "version_details": version_details,
    }


def _load_sync_config() -> Any:
    from ai_config_sync.sync import default_paths, load_sync_config
    return load_sync_config(default_paths(REPO_ROOT, None).config_path)


def _read_text(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _read_paseo_server_version(install_root: str | None) -> str | None:
    if not install_root:
        return None
    package_json = Path(install_root) / "lib" / "node_modules" / "@getpaseo" / "cli" / "node_modules" / "@getpaseo" / "server" / "package.json"
    payload = _read_json_file(package_json)
    version = payload.get("version")
    return version if isinstance(version, str) and version.strip() else None


def _read_paseo_desktop_client_version(log_path: str | None) -> str | None:
    if not log_path:
        return None
    path = Path(log_path)
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - 131072, 0), os.SEEK_SET)
            text = handle.read().decode("utf-8", errors="ignore")
    except OSError:
        return None
    matches = re.findall(r"Paseo/(\d+\.\d+\.\d+)", text)
    return matches[-1] if matches else None


def _read_serena_state_entries() -> list[dict[str, Any]]:
    state_root = REPO_ROOT / "vendor" / "mcp" / "serena-manager" / "state"
    entries: list[dict[str, Any]] = []
    for meta_path in sorted(state_root.glob("*/meta.json")):
        payload = _read_json_file(meta_path)
        project_root = payload.get("project_root")
        pid = payload.get("pid")
        if not isinstance(project_root, str) or not project_root or not isinstance(pid, int):
            continue
        entries.append(
            {
                "project_root": project_root,
                "project_hash": payload.get("project_hash"),
                "agent_pid": pid,
                "endpoint_url": payload.get("endpoint_url"),
                "status": payload.get("status"),
                "started_at": payload.get("started_at"),
                "last_active_at": payload.get("last_active_at"),
                "manager_log_path": str(meta_path.parent / "manager.log"),
            }
        )
    return entries


def _extract_skill_description(prompt: str) -> str | None:
    in_frontmatter = False
    collecting_block = False
    block_lines: list[str] = []
    for raw_line in prompt.splitlines():
        line = raw_line.strip()
        if line == "---":
            if in_frontmatter and collecting_block:
                return " ".join(part for part in block_lines if part).strip() or None
            in_frontmatter = not in_frontmatter
            continue
        if collecting_block:
            if raw_line.startswith((" ", "\t")):
                block_lines.append(line)
                continue
            return " ".join(part for part in block_lines if part).strip() or None
        if in_frontmatter:
            match = re.match(r'description:\s*(.*?)$', line)
            if match:
                value = match.group(1).strip()
                if value in {">", "|", ">-", "|-", ">+", "|+"}:
                    collecting_block = True
                    block_lines = []
                    continue
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]
                return value.strip() or None
    if collecting_block:
        return " ".join(part for part in block_lines if part).strip() or None
    return None


SKILL_ZH_LABELS: dict[str, str] = {
    "accessibility": "无障碍改进",
    "agents-self-evolution": "规则与记忆演进",
    "architecture-deepening": "架构深入检查",
    "aspnet-core": "ASP.NET Core 开发",
    "aspnet-modular-autofac": "ASP.NET 模块化依赖注入",
    "clarify-with-repo-context": "结合仓库上下文澄清需求",
    "code-maintainability": "代码可维护性检查",
    "code-review": "代码审查",
    "codex-subagent": "Codex 子代理协作",
    "core-web-vitals": "核心网页指标优化",
    "csharp-symbolic-workflow": "C# 符号级工作流",
    "database-workflow": "数据库工作流",
    "dependency-upgrade": "依赖升级",
    "design-review": "设计审查",
    "document-workflow": "文档工作流",
    "fast-codebase-retrieval": "快速代码检索",
    "film-explainer-remix": "影视解说改写",
    "frontend-design": "前端视觉设计",
    "frontend-design-review": "前端设计评审",
    "frontend-ui-engineering": "前端界面工程",
    "gh-address-comments": "处理 GitHub 评论",
    "gh-fix-ci": "修复 GitHub CI",
    "git-commit": "提交信息生成",
    "imagegen": "图像生成与编辑",
    "java-spring-workflow": "Java Spring 工作流",
    "large-refactor": "大型重构",
    "mcp-builder": "MCP 构建",
    "openai-docs": "OpenAI 官方文档助手",
    "parallel-execution": "并行执行决策",
    "performance": "性能优化",
    "playwright-browser-regression": "Playwright 浏览器回归检查",
    "plugin-creator": "插件创建",
    "project-orchestration": "项目编排",
    "release-workflow": "发布工作流",
    "security-review": "安全审查",
    "serena-workflow": "Serena 工作流",
    "skill-creator": "技能创建",
    "skill-installer": "技能安装",
    "systematic-debugging": "系统化调试",
    "test-driven-development": "测试驱动开发",
    "ui-styling": "界面样式",
    "ui-ux-pro-max": "UI/UX 参考库",
    "using-superpowers": "默认超能力工作模式",
    "web-quality-audit": "网页质量审计",
    "writing-plans": "编写实施计划",
    "pi-autonomy-orchestrator": "Pi 自主编排",
}


def _skill_zh_label(name: str) -> str:
    return SKILL_ZH_LABELS.get(name, name.replace("-", " "))


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _refresh_prompt_outputs(config: Any) -> None:
    from ai_config_sync.sync import build_global_prompt, sync_global_prompt

    targets = (
        config.codex,
        config.claude,
        config.opencode,
        config.pi,
    )
    for target in targets:
        if target is None or getattr(target, "global_prompt_path", None) is None:
            continue
        prompt_text = build_global_prompt(config.global_prompt_path, target.global_prompt_append_path)
        if prompt_text is not None:
            sync_global_prompt(target.global_prompt_path, prompt_text)


def _get_target_config(config: Any, tool: str) -> Any:
    if tool == "codex":
        return config.codex
    if tool == "claude":
        return config.claude
    if tool == "opencode":
        return config.opencode
    if tool == "pi":
        return config.pi
    raise KeyError(tool)


def _get_prompt_payload(tool: str) -> dict[str, Any]:
    config = _load_sync_config()
    target = _get_target_config(config, tool)
    if target is None:
        raise KeyError(tool)

    from ai_config_sync.sync import build_global_prompt

    shared_path = getattr(config, "global_prompt_path", None)
    overlay_path = getattr(target, "global_prompt_append_path", None)
    effective_path = getattr(target, "global_prompt_path", None)
    effective_text = build_global_prompt(shared_path, overlay_path)
    if effective_text is None:
        effective_text = _read_text(effective_path)

    return {
        "tool": tool,
        "label": TOOLS[tool]["label"],
        "shared": {
            "path": str(shared_path) if shared_path else None,
            "text": _read_text(shared_path),
            "editable": shared_path is not None,
        },
        "overlay": {
            "path": str(overlay_path) if overlay_path else None,
            "text": _read_text(overlay_path),
            "editable": overlay_path is not None,
        },
        "effective": {
            "path": str(effective_path) if effective_path else None,
            "text": effective_text,
            "editable": False,
        },
    }


def _save_prompt_source(tool: str, scope: str, content: str) -> dict[str, Any]:
    config = _load_sync_config()
    target = _get_target_config(config, tool)
    if target is None:
        raise KeyError(tool)

    if scope == "shared":
        path = getattr(config, "global_prompt_path", None)
    elif scope == "overlay":
        path = getattr(target, "global_prompt_append_path", None)
    else:
        raise ValueError(scope)

    if path is None:
        raise FileNotFoundError(f"{tool}:{scope}")

    _write_text(path, content)
    _refresh_prompt_outputs(config)
    return _get_prompt_payload(tool)


def _normalize_process_state(raw_status: str) -> tuple[str, str]:
    status = raw_status.lower()
    mapping = {
        "running": ("执行中", "green"),
        "sleeping": ("等待中", "blue"),
        "disk-sleep": ("IO 等待", "yellow"),
        "idle": ("空闲", "muted"),
        "stopped": ("已暂停", "red"),
        "tracing-stop": ("调试暂停", "yellow"),
        "zombie": ("僵尸", "red"),
        "dead": ("已终止", "red"),
        "wake-kill": ("唤醒中止", "yellow"),
        "waking": ("唤醒中", "blue"),
        "parked": ("挂起等待", "muted"),
        "locked": ("锁等待", "yellow"),
        "waiting": ("等待中", "blue"),
        "suspended": ("挂起", "yellow"),
    }
    return mapping.get(status, (raw_status, "muted"))


def _paseo_status() -> dict[str, Any]:
    launcher = _find_paseo_launcher()
    path_info = _command_location("paseo")
    if launcher is not None and path_info["launcher_path"] is None:
        resolved_launcher = _safe_resolve(launcher)
        install_root: Path | None = None
        if (
            resolved_launcher is not None
            and resolved_launcher.name == "paseo"
            and len(resolved_launcher.parents) >= 6
            and resolved_launcher.parts[-6:] == ("lib", "node_modules", "@getpaseo", "cli", "bin", "paseo")
        ):
            install_root = resolved_launcher.parents[5]
        elif launcher.parent.name == "bin":
            install_root = launcher.parent.parent
        path_info = {
            "launcher_path": str(launcher),
            "resolved_path": str(resolved_launcher) if resolved_launcher else None,
            "install_root": str(install_root) if install_root else None,
        }
    installed = _cmd_version("paseo")
    if installed is None and launcher is not None:
        try:
            r = _run([str(launcher), "--version"], timeout=10)
            out = (r.stdout or r.stderr).strip()
            m = re.search(r"(\d+\.\d+[\.\d]*)", out)
            installed = m.group(1) if m else (out[:30] or None)
        except Exception:
            pass
    latest = _npm_latest("@getpaseo/cli")
    payload: dict[str, Any] = {}
    if launcher is not None:
        try:
            proc = _run([str(launcher), "status", "--json"], timeout=20)
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except Exception:
            payload = {}

    local_daemon = payload.get("localDaemon")
    service_status = "active" if local_daemon == "running" else "inactive"
    cli_version = payload.get("cliVersion") or installed
    daemon_version = payload.get("daemonVersion") or _read_paseo_server_version(path_info["install_root"])
    desktop_client_version = _read_paseo_desktop_client_version(payload.get("logPath"))
    current_version = daemon_version or cli_version or installed
    return {
        "key": "paseo",
        "label": TOOLS["paseo"]["label"],
        "color": TOOLS["paseo"]["color"],
        "installed": current_version,
        "latest": latest,
        "has_update": bool(current_version and latest and current_version != latest),
        "status": service_status,
        "service": service_status,
        "service_status": service_status,
        "service_manageable": launcher is not None,
        "service_manage_label": "本地守护进程",
        "launcher_path": path_info["launcher_path"],
        "resolved_path": path_info["resolved_path"],
        "install_root": path_info["install_root"],
        "service_name": "paseo daemon" if launcher is not None else None,
        "service_path": payload.get("home"),
        "daemon_home": payload.get("home"),
        "daemon_log_path": payload.get("logPath"),
        "listen": payload.get("listen"),
        "relay": payload.get("relay"),
        "pid": payload.get("pid"),
        "connected_daemon": payload.get("connectedDaemon"),
        "cli_version": cli_version,
        "daemon_version": daemon_version,
        "desktop_client_version": desktop_client_version,
        "desktop_managed": payload.get("desktopManaged"),
    }


def _run_paseo_action(action: str) -> dict[str, Any]:
    launcher = _find_paseo_launcher()
    if launcher is None:
        raise FileNotFoundError("paseo launcher not found on PATH")

    status = _paseo_status()
    home = status.get("daemon_home") or str(Path.home() / ".paseo")
    if action == "start":
        args = [str(launcher), "start", "--home", home]
        if isinstance(status.get("listen"), str) and status["listen"].strip():
            args.extend(["--listen", status["listen"].strip()])
        relay = status.get("relay")
        if relay in (None, "", "disabled", False):
            args.append("--no-relay")
        elif isinstance(relay, str) and relay.startswith("wss://"):
            args.append("--relay-use-tls")
    elif action == "stop":
        args = [str(launcher), "daemon", "stop", "--home", home]
    else:
        raise ValueError(action)

    result = _run(args, timeout=30)
    return {
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "status": _paseo_status(),
    }


def _process_matches_tool(tool: str, name: str, cmdline: list[str]) -> bool:
    parts = [Path(part).name.lower() for part in cmdline if part]
    text = " ".join(cmdline).lower()
    if tool == "codex":
        if name == "codex":
            return True
        if name == "node" and (" codex app-server" in f" {text}" or "@openai/codex" in text):
            return True
        return False
    if tool == "paseo":
        if "paseo daemon start" in text or "@getpaseo/" in text:
            return True
        if "paseo daemon" in name or "paseo superviso" in name:
            return True
        return False
    if name in TOOL_PROCS[tool]:
        return True
    for pattern in TOOL_PROCS[tool]:
        if pattern in parts:
            return True
        if len(pattern) > 3 and pattern in text:
            return True
    return False


def _is_runtime_process(tool: str, *, name: str, cmdline: list[str]) -> bool:
    if not _process_matches_tool(tool, name, cmdline):
        return False
    text = " ".join(cmdline).lower()
    if "--version" in text:
        return False
    if tool == "codex":
        return "app-server" in text
    if tool == "claude" and " auth status --json" in f" {text} ":
        return False
    if tool == "opencode":
        return " serve " in f" {text} "
    if tool == "paseo":
        if " paseo status " in f" {text} " or " paseo --version" in f" {text} ":
            return False
        if "terminal-worker-process.js" in text:
            return True
        return any(
            marker in text
            for marker in ("paseo daemon start", "@getpaseo/server", "@getpaseo/cli")
        ) or "paseo daemon" in name or "paseo superviso" in name
    return True


def _tool_process_status(tool: str) -> str:
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            info = proc.info
            name = (info["name"] or "").lower()
            cmdline = info["cmdline"] or []
            if _is_runtime_process(tool, name=name, cmdline=cmdline):
                return "active"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return "inactive"


def _process_kind(tool: str, cmdline: list[str]) -> str:
    text = " ".join(cmdline).lower()
    if tool == "codex":
        return "app-server"
    if tool == "claude":
        return "session"
    if tool == "opencode":
        if "--port 3000" in text:
            return "managed-service"
        return "server"
    if tool == "pi":
        return "interactive"
    if tool == "paseo":
        if "terminal-worker-process.js" in text:
            return "terminal-worker"
        if "daemon-worker.js" in text:
            return "daemon-worker"
        if "paseo daemon start" in text:
            return "daemon-launcher"
        if "paseo superviso" in text:
            return "supervisor"
        if "paseo daemon" in text:
            return "daemon"
        return "runtime"
    return "runtime"


def _list_skill_dir_entries(skills_dir: Path) -> list[str]:
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []
    skills: list[str] = []
    for item in sorted(skills_dir.iterdir()):
        if item.name.startswith("."):
            continue
        target = _safe_resolve(item)
        if target is None:
            continue
        if target.is_dir() and (target / "SKILL.md").exists():
            skills.append(item.name)
    return skills


def _skill_entry_from_path(name: str, skill_dir: Path, source: str) -> dict[str, Any] | None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        return None
    prompt = _read_text(skill_file)
    if prompt is None:
        return None
    return {
        "name": name,
        "zh_label": _skill_zh_label(name),
        "description": _extract_skill_description(prompt),
        "path": str(skill_dir),
        "skill_file": str(skill_file),
        "source": source,
    }


def _list_skill_entries(skills_dir: Path) -> list[dict[str, Any]]:
    if not skills_dir.exists() or not skills_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for item in sorted(skills_dir.iterdir()):
        if item.name.startswith("."):
            continue
        target = _safe_resolve(item)
        if target is None or not target.is_dir():
            continue
        entry = _skill_entry_from_path(item.name, target, "filesystem")
        if entry is not None:
            entries.append(entry)
    return entries


def _list_builtin_skill_entries(native_dir: Path | None) -> list[dict[str, Any]]:
    if native_dir is None or not native_dir.exists() or not native_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for hidden_group in sorted(native_dir.iterdir()):
        if not hidden_group.is_dir() or not hidden_group.name.startswith("."):
            continue
        for item in sorted(hidden_group.iterdir()):
            if not item.is_dir():
                continue
            entry = _skill_entry_from_path(item.name, item, "builtin")
            if entry is not None:
                entry["group"] = hidden_group.name
                entries.append(entry)
    return entries


def _resolved_skill_to_entry(skill: Any, source: str) -> dict[str, Any]:
    name = getattr(skill, "name", "") or ""
    source_dir = getattr(skill, "source_dir", None)
    skill_file = getattr(skill, "skill_file", None)
    description = getattr(skill, "description", None)
    if description in {None, "", ">", "|", ">-", "|-", ">+", "|+"} and skill_file:
        prompt = _read_text(Path(str(skill_file)))
        if prompt is not None:
            description = _extract_skill_description(prompt)
    return {
        "name": name,
        "zh_label": _skill_zh_label(name),
        "description": description,
        "path": str(source_dir) if source_dir else None,
        "skill_file": str(skill_file) if skill_file else None,
        "source": source,
    }


def _list_opencode_agent_entries(config_path: Path, agent_prefix: str) -> list[str]:
    try:
        from ai_config_sync.sync import _load_jsonc
        payload = _load_jsonc(config_path)
    except Exception:
        return []
    agents = payload.get("agent")
    if not isinstance(agents, dict):
        return []
    return sorted(
        key.removeprefix(agent_prefix)
        for key in agents
        if isinstance(key, str) and key.startswith(agent_prefix)
    )


def _list_opencode_agent_entry_details(
    config_path: Path,
    agent_prefix: str,
    known_skills: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    names = _list_opencode_agent_entries(config_path, agent_prefix)
    entries: list[dict[str, Any]] = []
    for name in names:
        known = known_skills.get(name, {})
        entries.append({
            "name": name,
            "zh_label": _skill_zh_label(name),
            "description": known.get("description"),
            "path": known.get("path"),
            "skill_file": known.get("skill_file"),
            "source": "config-agent",
        })
    return entries


def _classify_mcp_process(name: str, cmdline: list[str]) -> tuple[str, str] | None:
    text = " ".join(cmdline).lower()
    if "mcp-server-fetch" in text or name.startswith("mcp-server-fetc"):
        return "fetch", "server"
    if "serena_manager.launcher" in text:
        return "serena", "manager"
    if "serena-agent/runner.py" in text and "start-mcp-server" in text:
        return "serena", "agent"
    if "vendor/mcp/node-repl-linux/index.mjs" in text:
        return "node_repl", "server"
    if "codegraph.js" in text and "serve --mcp" in text and "process.kill(parentpid" not in text:
        return "codegraph", "server"
    return None


def _process_parent_meta(proc: psutil.Process) -> dict[str, Any]:
    try:
        parent = proc.parent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        parent = None
    if parent is None:
        return {
            "parent_pid": None,
            "parent_name": None,
            "parent_cmd": None,
            "parent_cwd": None,
        }
    try:
        parent_cmdline = parent.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        parent_cmdline = []
    try:
        parent_cwd = parent.cwd()
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        parent_cwd = None
    try:
        parent_name = parent.name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        parent_name = None
    return {
        "parent_pid": parent.pid,
        "parent_name": parent_name,
        "parent_cmd": " ".join(part.strip() for part in parent_cmdline if part and part.strip()) or None,
        "parent_cwd": parent_cwd,
    }


def _process_ancestor_cwds(proc: psutil.Process, *, max_depth: int = 8) -> list[str]:
    ancestor_cwds: list[str] = []
    seen: set[int] = set()
    current: psutil.Process | None = proc
    depth = 0
    while current is not None and depth < max_depth:
        try:
            current = current.parent()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
        if current is None:
            break
        try:
            pid = current.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            break
        if pid in seen:
            break
        seen.add(pid)
        try:
            cwd = current.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            cwd = None
        if cwd:
            ancestor_cwds.append(cwd)
        depth += 1
    return ancestor_cwds


def _process_descendant_cwds(proc: psutil.Process, *, max_depth: int = 24) -> list[str]:
    descendant_cwds: list[str] = []
    try:
        descendants = proc.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return descendant_cwds
    for child in descendants[:max_depth]:
        try:
            cwd = child.cwd()
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            cwd = None
        if cwd:
            descendant_cwds.append(cwd)
    return descendant_cwds


def _normalize_project_root(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(Path(value).expanduser().resolve())
    except OSError:
        return str(Path(value).expanduser())


def _project_hint_from_process(entry: dict[str, Any]) -> str | None:
    if entry.get("tool") == "paseo":
        return None
    explicit = _normalize_project_root(entry.get("project_root"))
    if explicit:
        return explicit
    home = str(Path.home().resolve())
    candidates: list[str | None] = [
        _normalize_project_root(entry.get("cwd")),
        _normalize_project_root(entry.get("parent_cwd")),
    ]
    candidates.extend(_normalize_project_root(value) for value in entry.get("ancestor_cwds", []))
    candidates.extend(_normalize_project_root(value) for value in entry.get("descendant_cwds", []))
    project_candidates = [
        candidate
        for candidate in candidates
        if candidate and candidate != home and "/projects/" in candidate
    ]
    if project_candidates:
        return min(project_candidates, key=lambda value: (len(Path(value).parts), len(value)))
    for candidate in candidates:
        if not candidate or candidate == home:
            continue
        return candidate
    return None


def _listening_pids() -> set[int]:
    try:
        connections = psutil.net_connections(kind="tcp")
    except (psutil.Error, OSError, ValueError):
        return set()
    listening: set[int] = set()
    for connection in connections:
        status = getattr(connection, "status", None)
        pid = getattr(connection, "pid", None)
        if pid and status in {psutil.CONN_LISTEN, "LISTEN"}:
            listening.add(int(pid))
    return listening


def _annotate_paseo_processes(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not processes:
        return []

    pid_map = {int(process["pid"]): process for process in processes}
    child_map: dict[int, list[int]] = {}
    for process in processes:
        parent_pid = process.get("parent_pid")
        if isinstance(parent_pid, int):
            child_map.setdefault(parent_pid, []).append(int(process["pid"]))

    primary_daemon_pids = sorted(
        pid
        for pid, process in pid_map.items()
        if process.get("kind") == "daemon" and pid in _listening_pids()
    )
    if not primary_daemon_pids:
        daemon_pids = sorted(
            pid for pid, process in pid_map.items() if process.get("kind") == "daemon"
        )
        if daemon_pids:
            primary_daemon_pids = [daemon_pids[-1]]

    primary_pids: set[int] = set()
    for daemon_pid in primary_daemon_pids:
        root_pid = daemon_pid
        seen_chain = {daemon_pid}
        while True:
            parent_pid = pid_map.get(root_pid, {}).get("parent_pid")
            if not isinstance(parent_pid, int) or parent_pid not in pid_map or parent_pid in seen_chain:
                break
            seen_chain.add(parent_pid)
            root_pid = parent_pid

        stack = [root_pid]
        while stack:
            current_pid = stack.pop()
            if current_pid in primary_pids:
                continue
            primary_pids.add(current_pid)
            stack.extend(sorted(child_map.get(current_pid, ()), reverse=True))

    if not primary_pids:
        primary_pids = {int(process["pid"]) for process in processes}

    annotated: list[dict[str, Any]] = []
    for process in sorted(
        processes,
        key=lambda item: (0 if int(item["pid"]) in primary_pids else 1, int(item["pid"])),
    ):
        pid = int(process["pid"])
        cluster = "primary" if pid in primary_pids else "residual"
        annotated.append(
            {
                **process,
                "cluster": cluster,
                "primary": cluster == "primary",
                "residual": cluster == "residual",
            }
        )
    return annotated


def _proc_rss_bytes(proc: psutil.Process) -> int:
    try:
        return int(proc.memory_info().rss)
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, AttributeError, ValueError):
        return 0


def _sum_rss_bytes(processes: list[dict[str, Any]]) -> int:
    total = 0
    for process in processes:
        try:
            total += int(process.get("rss_bytes") or 0)
        except (TypeError, ValueError):
            continue
    return total


def _kind_counts(processes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for process in processes:
        kind = str(process.get("kind") or "server")
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _build_generic_mcp_process_groups(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for process in sorted(processes, key=lambda item: int(item["pid"])):
        project_root = _project_hint_from_process(process)
        if project_root:
            key = f"project:{project_root}"
            label = project_root
        else:
            owner_pid = process.get("parent_pid") or process["pid"]
            owner_name = process.get("parent_name") or "未知会话"
            key = f"owner:{owner_pid}"
            label = f"未归属会话 · {owner_name}#{owner_pid}"
        bucket = grouped.setdefault(
            key,
            {
                "project_root": project_root,
                "label": label,
                "pids": [],
                "processes": [],
            },
        )
        bucket["pids"].append(int(process["pid"]))
        bucket["processes"].append(process)

    results: list[dict[str, Any]] = []
    for group in grouped.values():
        processes_in_group = group["processes"]
        results.append(
            {
                "project_root": group["project_root"],
                "label": group["label"],
                "process_count": len(processes_in_group),
                "rss_bytes": _sum_rss_bytes(processes_in_group),
                "kind_counts": _kind_counts(processes_in_group),
                "pids": group["pids"],
                "processes": processes_in_group,
                "unmapped": group["project_root"] is None,
            }
        )
    return sorted(results, key=lambda item: (item.get("project_root") is None, str(item.get("label") or "")))


def _build_serena_process_groups(processes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    state_entries = _read_serena_state_entries()
    live_agents_by_project: dict[str, list[dict[str, Any]]] = {}
    live_managers: list[dict[str, Any]] = []
    for process in processes:
        if process.get("kind") == "agent" and process.get("project_root"):
            live_agents_by_project.setdefault(str(process["project_root"]), []).append(process)
        elif process.get("kind") == "manager":
            live_managers.append(process)

    known_project_roots = {
        str(entry["project_root"])
        for entry in state_entries
    } | set(live_agents_by_project)
    ambiguous_manager_roots = {
        root
        for root in known_project_roots
        if any(
            other != root and other.startswith(root.rstrip("/") + "/")
            for other in known_project_roots
        )
    }

    matched_manager_pids: set[int] = set()
    groups: list[dict[str, Any]] = []

    for state in state_entries:
        project_root = str(state["project_root"])
        agents = sorted(
            live_agents_by_project.pop(project_root, []),
            key=lambda item: int(item["pid"]),
        )
        managers = [] if project_root in ambiguous_manager_roots else [
            manager
            for manager in live_managers
            if manager.get("parent_cwd") == project_root
        ]
        for manager in managers:
            matched_manager_pids.add(int(manager["pid"]))
        if not agents and not managers:
            continue
        combined = sorted(
            [*managers, *agents],
            key=lambda item: (0 if item.get("kind") == "manager" else 1, int(item["pid"])),
        )
        groups.append(
            {
                "project_root": project_root,
                "project_hash": state.get("project_hash"),
                "endpoint_url": state.get("endpoint_url"),
                "status": state.get("status"),
                "started_at": state.get("started_at"),
                "last_active_at": state.get("last_active_at"),
                "manager_log_path": state.get("manager_log_path"),
                "agent_count": len(agents),
                "manager_count": len(managers),
                "rss_bytes": _sum_rss_bytes(combined),
                "pids": [int(item["pid"]) for item in combined],
                "processes": combined,
            }
        )

    for project_root, agents in sorted(live_agents_by_project.items()):
        sorted_agents = sorted(agents, key=lambda item: int(item["pid"]))
        groups.append(
            {
                "project_root": project_root,
                "project_hash": None,
                "endpoint_url": None,
                "status": "running",
                "started_at": None,
                "last_active_at": None,
                "manager_log_path": None,
                "agent_count": len(sorted_agents),
                "manager_count": 0,
                "rss_bytes": _sum_rss_bytes(sorted_agents),
                "pids": [int(item["pid"]) for item in sorted_agents],
                "processes": sorted_agents,
            }
        )

    unmatched_managers = [
        manager
        for manager in live_managers
        if int(manager["pid"]) not in matched_manager_pids
    ]
    if unmatched_managers:
        groups.append(
            {
                "project_root": "未归属 launcher",
                "project_hash": None,
                "endpoint_url": None,
                "status": "running",
                "started_at": None,
                "last_active_at": None,
                "manager_log_path": None,
                "agent_count": 0,
                "manager_count": len(unmatched_managers),
                "rss_bytes": _sum_rss_bytes(unmatched_managers),
                "pids": [int(item["pid"]) for item in unmatched_managers],
                "processes": sorted(unmatched_managers, key=lambda item: int(item["pid"])),
                "unmapped": True,
            }
        )

    return sorted(groups, key=lambda item: (item.get("project_root") == "未归属 launcher", str(item["project_root"])))


def _list_mcp_processes() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time"]):
        try:
            info = proc.info
            name = (info["name"] or "").lower()
            cmdline = info["cmdline"] or []
            if not cmdline:
                continue
            match = _classify_mcp_process(name, cmdline)
            if match is None:
                continue
            mcp_name, kind = match
            cmd = " ".join(part.strip() for part in cmdline if part and part.strip())
            state_label, state_tone = _normalize_process_state(str(info["status"]))
            entry = {
                "pid": info["pid"],
                "name": info["name"],
                "cmd": cmd,
                "kind": kind,
                "rss_bytes": _proc_rss_bytes(proc),
                "raw_status": info["status"],
                "state_label": state_label,
                "state_tone": state_tone,
                "project_root": _argv_option(cmdline, "--project", "--path"),
            }
            entry.update(_process_parent_meta(proc))
            grouped.setdefault(mcp_name, []).append(entry)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return grouped


def _stream_command(
    cmd: list[str],
    emit: Any,
    *,
    sudo_password: str | None = None,
    require_sudo: bool = False,
) -> None:
    actual_cmd = list(cmd)
    if require_sudo:
        if not sudo_password:
            raise PermissionError("该操作需要 sudo 密码，请先在设置中保存 sudo 密码")
        actual_cmd = ["/usr/bin/sudo", "-S", "-p", "", "--", *cmd]
    emit(f"$ {' '.join(actual_cmd)}")
    proc = subprocess.Popen(
        actual_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.PIPE if require_sudo else None,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if require_sudo and proc.stdin is not None:
        proc.stdin.write(sudo_password + "\n")
        proc.stdin.flush()
        proc.stdin.close()
    assert proc.stdout is not None
    for line in proc.stdout:
        emit(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, actual_cmd)


def _get_tool_status(key: str) -> dict[str, Any]:
    meta = TOOLS[key]
    installed: str | None = None
    latest: str | None = None
    status: str = "n/a"
    service_status: str = "n/a"
    service_manageable = False
    path_info = _command_location(meta["cmd"])
    service_name: str | None = None
    service_path: str | None = None
    install_root = path_info["install_root"]
    service_manage_label = "systemd 服务"
    web_url: str | None = None
    web_port: int | None = None
    web_host: str | None = None
    pi_web: dict[str, Any] | None = None
    packages: dict[str, Any] | None = None

    if key == "paseo":
        return _paseo_status()
    if key == "opencode":
        try:
            from ai_config_sync.opencode_manager import opencode_status
            st = opencode_status()
            installed = st.get("current_version")
            service_status = st.get("service_active", "unknown")
            status = "active" if _tool_process_status("opencode") == "active" else service_status
            path_info = {
                "launcher_path": st.get("launcher_path"),
                "resolved_path": st.get("current_target") or st.get("launcher_path"),
                "install_root": st.get("current_target") or install_root,
            }
            install_root = st.get("current_target") or install_root
            service_name = st.get("service_name")
            service_path = st.get("service_path")
            web = _service_web_details(
                str(service_name),
                host_flags=("--hostname", "--host"),
                port_flags=("--port",),
            ) if service_name else {}
        except Exception:
            web = {}
            pass
        try:
            from ai_config_sync.opencode_manager import _latest_opencode_version
            latest = _latest_opencode_version()
        except Exception:
            latest = _github_latest(meta["github"])
        service_manageable = True
        web_url = web.get("url")
        web_port = web.get("port")
        web_host = web.get("host")
    elif key == "pi":
        packages = {"managed_entries": [], "managed_specs": [], "installed_package_versions": {}, "declared_dependencies": {}}
        try:
            from ai_config_sync.pi_manager import pi_status
            from ai_config_sync.pi_web_manager import pi_web_status
            pi = pi_status()
            installed = pi.get("version")
            path_info["launcher_path"] = pi.get("launcher_path") or path_info["launcher_path"]
            path_info["resolved_path"] = str(_safe_resolve(Path(pi["launcher_path"]))) if pi.get("launcher_path") else path_info["resolved_path"]
            install_root = pi.get("install_prefix") or install_root
            pi_web = pi_web_status()
            web_service_name = pi_web.get("service_name")
            web_details = _service_web_details(
                str(web_service_name),
                host_flags=("--host", "--hostname"),
                port_flags=("--port",),
            ) if web_service_name else {}
            latest_pi_web = _github_latest_redirect("https://github.com/Epsilondelta-ai/pi-web/releases/latest")
            if latest_pi_web and not latest_pi_web.startswith("v"):
                latest_pi_web = f"v{latest_pi_web}"
            pi_web["latest_version"] = latest_pi_web
            pi_web["has_update"] = bool(pi_web.get("version") and pi_web.get("latest_version") and pi_web["version"] != pi_web["latest_version"])
            pi_web["url"] = web_details.get("url")
            pi_web["port"] = web_details.get("port")
            pi_web["hostname"] = web_details.get("host")
        except Exception:
            pi_web = {}
            pass
        try:
            from ai_config_sync.pi_package_manager import inspect_pi_packages
            from ai_config_sync.sync import default_paths, load_sync_config
            paths = default_paths(REPO_ROOT, None)
            config = load_sync_config(paths.config_path)
            if config.pi is not None:
                packages = inspect_pi_packages(
                    settings_path=config.pi.settings_path,
                    packages=config.pi.packages,
                    latest_version_resolver=_cached_npm_latest,
                )
        except Exception:
            pass
        if installed is None:
            installed = _cmd_version(meta["cmd"])
        latest = _npm_latest(meta["npm"])
        status = _tool_process_status("pi")
        service_manageable = bool(pi_web.get("launcher_exists")) if pi_web else False
        service_status = pi_web.get("service_active", "inactive") if pi_web else "inactive"
        service_name = pi_web.get("service_name") if pi_web else None
        service_path = pi_web.get("service_path") if pi_web else None
        service_manage_label = "pi-web 托管服务"
        web_url = pi_web.get("url") if pi_web else None
        web_port = pi_web.get("port") if pi_web else None
        web_host = pi_web.get("hostname") if pi_web else None
    else:
        installed = _cmd_version(meta["cmd"])
        latest = _npm_latest(meta["npm"])
        status = _tool_process_status(key)
        if key == "claude":
            service_status = _service_status("claude-code.service")

    if status == "n/a":
        status = service_status

    settings = _load_settings()
    override_host = settings.get("web_host", "").strip()
    if override_host and web_url:
        try:
            from urllib.parse import urlparse, urlunparse
            p = urlparse(web_url)
            port_part = f":{p.port}" if p.port else ""
            override_url = urlunparse(p._replace(netloc=f"{override_host}{port_part}"))
            web_url = override_url
            web_host = override_host
            if pi_web is not None:
                pi_web["url"] = override_url
                pi_web["hostname"] = override_host
        except Exception:
            pass

    return {
        "key": key, "label": meta["label"], "color": meta["color"],
        "installed": installed, "latest": latest,
        "has_update": bool(installed and latest and installed != latest),
        "status": status,
        "service": status,
        "service_status": service_status,
        "service_manageable": service_manageable,
        "service_manage_label": service_manage_label if service_manageable else None,
        "launcher_path": path_info["launcher_path"],
        "resolved_path": path_info["resolved_path"],
        "install_root": install_root,
        "service_name": service_name,
        "service_path": service_path,
        "web_url": web_url,
        "web_port": web_port,
        "web_host": web_host,
        "pi_web": pi_web if key == "pi" else None,
        "pi_packages": packages if key == "pi" else None,
    }


def _get_sync_service_status() -> dict[str, Any]:
    try:
        from ai_config_sync.sync import default_paths, service_status
        return service_status(default_paths(REPO_ROOT, None))
    except Exception as exc:
        return {"error": str(exc)}


def _list_mcp_servers() -> list[dict[str, Any]]:
    try:
        config = _load_sync_config()
    except Exception:
        return []
    mcp_processes = _list_mcp_processes()
    servers: list[dict[str, Any]] = []
    for server in config.mcp_servers:
        payload = {
            "name": server.name,
            "type": server.transport,
            "transport": server.transport,
            "command": server.command,
            "args": list(server.args),
            "cwd": server.cwd,
            "url": server.url,
            "headers": server.headers,
            "tool_timeout_sec": server.tool_timeout_sec,
            "direct_tools": server.direct_tools,
            "enabled": server.enabled,
        }
        payload.update(_get_mcp_component_details(server.name))
        payload["processes"] = mcp_processes.get(server.name, [])
        payload["process_count"] = len(payload["processes"])
        payload["rss_bytes"] = _sum_rss_bytes(payload["processes"])
        payload["process_groups"] = (
            _build_serena_process_groups(payload["processes"])
            if server.name == "serena"
            else _build_generic_mcp_process_groups(payload["processes"])
        )
        servers.append(payload)
    return servers


_HOME_DIR = str(Path.home())
_SKIP_DIRS = {"/", _HOME_DIR}


def _get_proc_project_dir(proc: psutil.Process) -> str:
    """Return the project directory a process was launched from.

    Tries proc.cwd() first (actual cwd), then falls back to $PWD from the
    process environment (set by the shell at exec time, survives chdir).
    Filters out / and the user home dir as non-informative.
    """
    for getter in (lambda: proc.cwd(), lambda: proc.environ().get("PWD", "")):
        try:
            path = getter()
            if path and path not in _SKIP_DIRS:
                return path
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
    return ""


def _list_processes() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline", "status", "create_time"]):
        try:
            info = proc.info
            name = (info["name"] or "").lower()
            cmdline = info["cmdline"] or []
            if not cmdline:
                continue
            cmd = " ".join(part.strip() for part in cmdline if part and part.strip())
            if not cmd:
                continue
            for tool in TOOL_PROCS:
                if _is_runtime_process(tool, name=name, cmdline=cmdline):
                    state_label, state_tone = _normalize_process_state(str(info["status"]))
                    proc_cwd = _get_proc_project_dir(proc)
                    parent_meta = _process_parent_meta(proc)
                    try:
                        env = proc.environ()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                        env = {}
                    results.append({"tool": tool, "pid": info["pid"],
                                    "name": info["name"], "cmd": cmd,
                                    "cwd": proc_cwd,
                                    "kind": _process_kind(tool, cmdline), "status": info["status"],
                                    "rss_bytes": _proc_rss_bytes(proc),
                                    "raw_status": info["status"], "state_label": state_label,
                                    "state_tone": state_tone,
                                    "project_root": _paseo_agent_project_root(env.get("PASEO_AGENT_ID")) if tool in {"codex", "opencode"} else None,
                                    **parent_meta,
                                    "ancestor_cwds": _process_ancestor_cwds(proc),
                                    "descendant_cwds": _process_descendant_cwds(proc)})
                    break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    paseo_processes = [process for process in results if process["tool"] == "paseo"]
    if paseo_processes:
        paseo_by_pid = {
            int(process["pid"]): process
            for process in _annotate_paseo_processes(paseo_processes)
        }
        results = [
            paseo_by_pid.get(int(process["pid"]), process)
            if process["tool"] == "paseo"
            else process
            for process in results
        ]
    return results


def _get_agents_info() -> list[dict[str, Any]]:
    try:
        from ai_config_sync.sync import _legacy_default_target_paths, resolve_skills
        config = _load_sync_config()
    except Exception as exc:
        return [{"error": str(exc)}]

    shared_mcps = [{"name": m.name, "transport": m.transport, "shared": True}
                   for m in config.mcp_servers]
    shared_skill_objects = resolve_skills(config.skill_roots, config.include, allow_missing=True)
    shared_skills = [skill.name for skill in shared_skill_objects]
    shared_skill_entries = [_resolved_skill_to_entry(skill, "shared") for skill in shared_skill_objects]

    runtime_processes = _list_processes()
    processes_by_tool: dict[str, list[dict[str, Any]]] = {}
    for process in runtime_processes:
        processes_by_tool.setdefault(str(process["tool"]), []).append(process)

    mcp_processes = _list_mcp_processes()

    target_map: list[tuple[str, Any]] = [
        ("codex", config.codex), ("claude", config.claude),
        ("opencode", config.opencode), ("pi", config.pi),
    ]
    agents: list[dict[str, Any]] = []
    for key, target in target_map:
        if target is None:
            continue
        target_mcps = [{"name": m.name, "transport": m.transport, "shared": False}
                       for m in (target.mcp_servers or [])]
        tool_processes = processes_by_tool.get(key, [])
        tool_mcp_names = {m["name"] for m in shared_mcps + target_mcps}
        skills_dir = getattr(target, "skills_dir", None)
        skills_dir_path = Path(str(skills_dir)) if skills_dir else None
        target_skill_objects = resolve_skills(getattr(target, "skill_roots", ()), config.include, allow_missing=True)
        target_specific_skills = [skill.name for skill in target_skill_objects]
        target_skill_entries = [_resolved_skill_to_entry(skill, "target") for skill in target_skill_objects]
        effective_skill_objects = resolve_skills(config.skill_roots + getattr(target, "skill_roots", ()), config.include, allow_missing=True)
        effective_managed_skills = [skill.name for skill in effective_skill_objects]
        effective_skill_entries = [_resolved_skill_to_entry(skill, "effective") for skill in effective_skill_objects]
        effective_lookup = {entry["name"]: entry for entry in effective_skill_entries}
        if key == "opencode":
            synced_entries = _list_opencode_agent_entries(target.config_path, getattr(target, "agent_prefix", "skill-"))
            synced_skill_entries = _list_opencode_agent_entry_details(
                target.config_path,
                getattr(target, "agent_prefix", "skill-"),
                effective_lookup,
            )
            skills_source = "config-agent"
            native_skill_dirs: list[str] = []
            native_local_skills: list[str] = []
            builtin_skill_entries: list[dict[str, Any]] = []
        else:
            synced_entries = _list_skill_dir_entries(skills_dir_path) if skills_dir_path is not None else []
            synced_skill_entries = _list_skill_entries(skills_dir_path) if skills_dir_path is not None else []
            skills_source = "filesystem"
            native_dirs = []
            try:
                native_dirs = [
                    str(path)
                    for path in _legacy_default_target_paths(key)["skills_dirs"]
                    if path != skills_dir_path
                ]
            except Exception:
                native_dirs = []
            native_skill_dirs = native_dirs
            builtin_skill_entries = []
            for native_dir in native_dirs:
                builtin_skill_entries.extend(_list_builtin_skill_entries(Path(native_dir)))
            native_local_skills = [entry["name"] for entry in builtin_skill_entries]

        config_file = str(getattr(target, "config_path", None)
                          or getattr(target, "settings_path", "") or "")
        project_root = None
        if tool_processes:
            project_root = _project_hint_from_process(tool_processes[0])
        matched_mcp_processes = [
            process
            for name in tool_mcp_names
            for process in mcp_processes.get(name, [])
            if _project_hint_from_process(process) == project_root
        ] if project_root else []
        agents.append({
            "key": key,
            "label": TOOLS[key]["label"],
            "color": TOOLS[key]["color"],
            "project_root": project_root,
            "config_path": config_file,
            "skills_dir": str(skills_dir_path) if skills_dir_path is not None else None,
            "skills_source": skills_source,
            "global_prompt_path": str(getattr(target, "global_prompt_path", "") or "") or None,
            "global_prompt_append_path": str(getattr(target, "global_prompt_append_path", "") or "") or None,
            "shared_skill_roots": [str(root.path) for root in config.skill_roots],
            "target_skill_roots": [str(root.path) for root in getattr(target, "skill_roots", ())],
            "shared_skills": shared_skills,
            "shared_skill_entries": shared_skill_entries,
            "target_specific_skills": target_specific_skills,
            "target_skill_entries": target_skill_entries,
            "effective_managed_skills": effective_managed_skills,
            "effective_skill_entries": effective_skill_entries,
            "synced_entries": synced_entries,
            "synced_skill_entries": synced_skill_entries,
            "native_skill_dirs": native_skill_dirs,
            "native_local_skills": native_local_skills,
            "builtin_skill_entries": builtin_skill_entries,
            "mcp_servers": shared_mcps + target_mcps,
            "processes": tool_processes,
            "process_count": len(tool_processes),
            "process_rss_bytes": _sum_rss_bytes(tool_processes),
            "mcp_process_count": len(matched_mcp_processes),
            "mcp_rss_bytes": _sum_rss_bytes(matched_mcp_processes),
            "total_rss_bytes": _sum_rss_bytes(tool_processes) + _sum_rss_bytes(matched_mcp_processes),
            "skills": synced_entries,
        })
    return agents


def _validate_sudo(password: str) -> tuple[bool, str]:
    """Quick dry-run via fake-sudo to confirm password is correct."""
    import shlex, tempfile as _tmp
    td = _tmp.mkdtemp(prefix="ai-sudo-chk-")
    try:
        fake = os.path.join(td, "sudo")
        with open(fake, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\necho {shlex.quote(password)} | /usr/bin/sudo -S -p "" "$@"\n')
        os.chmod(fake, 0o700)
        env = {**os.environ, "PATH": td + os.pathsep + os.environ.get("PATH", "")}
        r = subprocess.run(["sudo", "-v"], env=env, capture_output=True, text=True, timeout=10)
        return r.returncode == 0, r.stderr.strip()
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _stream_script(script_path: Path, emit: Any, args: list[str] | None = None,
                   sudo_password: str | None = None) -> None:
    """Run a bash script, optionally injecting sudo password via a fake-sudo wrapper."""
    if not script_path.exists():
        raise FileNotFoundError(f"脚本未找到: {script_path}")

    import shlex, tempfile as _tmp
    env = os.environ.copy()
    tmpdir: str | None = None

    if sudo_password:
        # Inject password by putting a fake `sudo` ahead on PATH.
        # When the script calls `sudo <cmd>`, our wrapper runs:
        #   echo <password> | /usr/bin/sudo -S <cmd>
        tmpdir = _tmp.mkdtemp(prefix="ai-sudo-")
        fake = os.path.join(tmpdir, "sudo")
        with open(fake, "w", encoding="utf-8") as f:
            f.write(f'#!/bin/sh\necho {shlex.quote(sudo_password)} | /usr/bin/sudo -S -p "" "$@"\n')
        os.chmod(fake, 0o700)
        env["PATH"] = tmpdir + os.pathsep + env.get("PATH", "")
        emit("已注入 sudo 凭证代理")

    cmd = ["bash", str(script_path)] + (args or [])
    emit(f"$ {' '.join(cmd)}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", cwd=str(REPO_ROOT), env=env)
        for line in proc.stdout:  # type: ignore[union-attr]
            emit(line.rstrip())
        proc.wait()
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ─── app ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="AI Config Sync", docs_url=None, redoc_url=None)


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    return HTMLResponse((Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8"))


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    tools = await asyncio.gather(*[asyncio.to_thread(_get_tool_status, k) for k in TOOLS])
    sync_svc = await asyncio.to_thread(_get_sync_service_status)
    return {"tools": list(tools), "sync_service": sync_svc}


@app.get("/api/mcp")
async def api_mcp() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_mcp_servers)


@app.get("/api/processes")
async def api_processes() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_list_processes)


@app.get("/api/agents")
async def api_agents() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_get_agents_info)


@app.get("/api/prompts/{tool}")
async def api_prompt_get(tool: str) -> dict[str, Any]:
    if tool not in {"codex", "claude", "opencode", "pi"}:
        raise HTTPException(404, "未知工具")
    return await asyncio.to_thread(_get_prompt_payload, tool)


class PromptBody(BaseModel):
    scope: str
    content: str


@app.put("/api/prompts/{tool}")
async def api_prompt_put(tool: str, body: PromptBody) -> dict[str, Any]:
    if tool not in {"codex", "claude", "opencode", "pi"}:
        raise HTTPException(404, "未知工具")
    try:
        return await asyncio.to_thread(_save_prompt_source, tool, body.scope, body.content)
    except FileNotFoundError:
        raise HTTPException(400, "当前作用域没有可编辑的提示词文件")
    except ValueError:
        raise HTTPException(400, "未知提示词作用域")


@app.get("/api/settings")
async def api_settings_get() -> dict[str, Any]:
    s = _load_settings()
    # never expose the password value itself
    return {"has_sudo_password": bool(s.get("sudo_password")),
            "theme": s.get("theme", "light"),
            "web_host": s.get("web_host", "")}


class SettingsBody(BaseModel):
    sudo_password: str | None = None
    clear_sudo_password: bool = False
    theme: str | None = None
    web_host: str | None = None


@app.post("/api/settings")
async def api_settings_post(body: SettingsBody) -> dict[str, Any]:
    s = _load_settings()
    if body.clear_sudo_password:
        s.pop("sudo_password", None)
    elif body.sudo_password is not None:
        # validate before saving
        ok, err = await asyncio.to_thread(_validate_sudo, body.sudo_password)
        if not ok:
            raise HTTPException(400, f"密码验证失败: {err or '密码错误'}")
        s["sudo_password"] = body.sudo_password
    if body.theme is not None:
        s["theme"] = body.theme
    if body.web_host is not None:
        s["web_host"] = body.web_host
    _save_settings(s)
    return {"has_sudo_password": bool(s.get("sudo_password")), "theme": s.get("theme", "light"),
            "web_host": s.get("web_host", "")}


class KillBody(BaseModel):
    pids: list[int] = []
    all: bool = False
    tool: str | None = None


def _collect_process_tree(processes: list[psutil.Process]) -> list[psutil.Process]:
    seen: set[int] = set()
    collected: list[psutil.Process] = []
    for process in processes:
        try:
            descendants = process.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            descendants = []
        for candidate in [*descendants, process]:
            try:
                pid = candidate.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if pid in seen:
                continue
            seen.add(pid)
            collected.append(candidate)
    return sorted(collected, key=lambda proc: proc.pid, reverse=True)


def _terminate_process_tree(pids: list[int]) -> dict[str, list[Any]]:
    roots: list[psutil.Process] = []
    errors: list[str] = []
    for pid in sorted({int(pid) for pid in pids if pid}):
        try:
            roots.append(psutil.Process(pid))
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            errors.append(str(exc))

    tree = _collect_process_tree(roots)
    if not tree:
        return {"killed": [], "errors": errors}

    for process in tree:
        try:
            process.terminate()
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            errors.append(str(exc))

    gone, alive = psutil.wait_procs(tree, timeout=2.5)

    def _split_exited(processes: list[psutil.Process]) -> tuple[list[psutil.Process], list[psutil.Process]]:
        exited: list[psutil.Process] = []
        still_running: list[psutil.Process] = []
        for process in processes:
            try:
                status = process.status()
                running = process.is_running()
            except psutil.NoSuchProcess:
                exited.append(process)
                continue
            except psutil.AccessDenied:
                still_running.append(process)
                continue
            if not running or status == psutil.STATUS_ZOMBIE:
                exited.append(process)
            else:
                still_running.append(process)
        return exited, still_running

    exited_after_wait, alive = _split_exited(alive)
    for process in alive:
        try:
            process.kill()
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as exc:
            errors.append(str(exc))
    gone_after_kill, still_alive = psutil.wait_procs(alive, timeout=2.0)
    exited_after_kill, still_alive = _split_exited(still_alive)
    if still_alive:
        errors.extend(f"Failed to stop pid {process.pid}" for process in still_alive)

    killed = sorted(
        {
            process.pid
            for process in [*gone, *exited_after_wait, *gone_after_kill, *exited_after_kill]
        }
    )
    return {"killed": killed, "errors": errors}


@app.post("/api/processes/kill")
async def api_kill(body: KillBody) -> dict[str, Any]:
    if body.all:
        targets = [p["pid"] for p in _list_processes()]
    elif body.tool:
        targets = [p["pid"] for p in _list_processes() if p["tool"] == body.tool]
    else:
        targets = body.pids
    return _terminate_process_tree(targets)


class JobRequest(BaseModel):
    action: str
    tool: str | None = None
    mcp: str | None = None
    package: str | None = None
    version: str | None = None
    sudo_password: str | None = None   # override; falls back to stored setting


@app.post("/api/jobs")
async def api_create_job(req: JobRequest) -> dict[str, Any]:
    # resolve sudo password: request > stored setting
    sudo_pw: str | None = req.sudo_password or _load_settings().get("sudo_password")
    action = req.action

    if action in ("install", "update") and req.tool:
        meta = TOOLS.get(req.tool)
        if not meta:
            raise HTTPException(400, f"未知工具: {req.tool}")
        script = REPO_ROOT / meta["script"]
        version_args = [req.version] if req.version else []
        label = f"{'安装' if action == 'install' else '升级'} {meta['label']}"
        job = _spawn_job(label, lambda emit, s=script, va=version_args, pw=sudo_pw:
                         _stream_script(s, emit, va, pw))

    elif action == "sync":
        def _do_sync(emit: Any) -> None:
            from ai_config_sync.sync import default_paths, load_sync_config, sync_clients
            from ai_config_sync.mcp_runtime import preflight_mcp
            emit("运行 MCP 预检…")
            preflight_mcp(REPO_ROOT)
            paths = default_paths(REPO_ROOT, None)
            emit("同步客户端配置…")
            result = sync_clients(load_sync_config(paths.config_path), paths.state_path)
            emit(json.dumps(result, indent=2, ensure_ascii=False))
        job = _spawn_job("同步所有客户端", _do_sync)

    elif action == "mcp_update_all":
        def _do_mcp_update(emit: Any) -> None:
            from ai_config_sync.mcp_updates import update_all_mcp
            emit("更新所有 MCP 服务器…")
            result = update_all_mcp(REPO_ROOT)
            emit(json.dumps(result, indent=2, ensure_ascii=False))
        job = _spawn_job("更新所有 MCP", _do_mcp_update)

    elif action == "mcp_update" and req.mcp:
        def _do_mcp_single_update(emit: Any, mcp_name: str = req.mcp) -> None:
            from ai_config_sync.mcp_updates import (
                update_codegraph,
                update_fetch,
                update_node_repl_linux,
                update_serena_agent,
            )

            update_map = {
                "fetch": lambda: update_fetch(REPO_ROOT, version=req.version),
                "serena": lambda: update_serena_agent(REPO_ROOT, version=req.version),
                "codegraph": lambda: update_codegraph(REPO_ROOT, version=req.version),
                "node_repl": lambda: update_node_repl_linux(REPO_ROOT),
            }
            if mcp_name not in update_map:
                emit(f"{mcp_name} 暂不支持单独升级")
                return
            emit(f"升级 MCP: {mcp_name}")
            emit(json.dumps(update_map[mcp_name](), indent=2, ensure_ascii=False))

        job = _spawn_job(f"升级 MCP: {req.mcp}", _do_mcp_single_update)

    elif action == "service_start" and req.tool:
        def _do_start(emit: Any, tool: str = req.tool) -> None:
            if tool == "opencode":
                _stream_command(
                    [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "opencode-service-start"],
                    emit,
                    sudo_password=sudo_pw,
                    require_sudo=True,
                )
            elif tool == "pi":
                _stream_command(
                    [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "pi-web-service-start"],
                    emit,
                    sudo_password=sudo_pw,
                    require_sudo=True,
                )
            elif tool == "paseo":
                emit(json.dumps(_run_paseo_action("start"), indent=2, ensure_ascii=False))
            else:
                emit(f"{tool} 服务管理暂不支持")
        job = _spawn_job(f"启动 {req.tool} 服务", _do_start)

    elif action == "service_stop" and req.tool:
        def _do_stop(emit: Any, tool: str = req.tool) -> None:
            if tool == "opencode":
                _stream_command(
                    [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "opencode-service-stop"],
                    emit,
                    sudo_password=sudo_pw,
                    require_sudo=True,
                )
            elif tool == "pi":
                _stream_command(
                    [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "pi-web-service-stop"],
                    emit,
                    sudo_password=sudo_pw,
                    require_sudo=True,
                )
            elif tool == "paseo":
                emit(json.dumps(_run_paseo_action("stop"), indent=2, ensure_ascii=False))
            else:
                emit(f"{tool} 服务管理暂不支持")
        job = _spawn_job(f"停止 {req.tool} 服务", _do_stop)

    elif action == "pi_web_update":
        script = REPO_ROOT / "scripts" / "pi-web" / "update-pi-web.sh"
        job = _spawn_job("升级 Pi Web", lambda emit, s=script, pw=sudo_pw: _stream_script(s, emit, None, pw))

    elif action == "pi_web_service_start":
        def _do_pi_web_start(emit: Any) -> None:
            _stream_command(
                [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "pi-web-service-start"],
                emit,
                sudo_password=sudo_pw,
                require_sudo=True,
            )
        job = _spawn_job("启动 Pi Web 服务", _do_pi_web_start)

    elif action == "pi_web_service_stop":
        def _do_pi_web_stop(emit: Any) -> None:
            _stream_command(
                [str(REPO_ROOT / ".venv" / "bin" / "python"), "-m", "ai_config_sync.cli", "pi-web-service-stop"],
                emit,
                sudo_password=sudo_pw,
                require_sudo=True,
            )
        job = _spawn_job("停止 Pi Web 服务", _do_pi_web_stop)

    elif action == "pi_packages_upgrade":
        def _do_pi_packages_upgrade(emit: Any) -> None:
            from ai_config_sync.pi_package_manager import upgrade_pi_packages
            from ai_config_sync.sync import default_paths, load_sync_config
            paths = default_paths(REPO_ROOT, None)
            config = load_sync_config(paths.config_path)
            if config.pi is None:
                raise RuntimeError("当前未配置 Pi")
            emit("升级 Pi 自定义组件…")
            result = upgrade_pi_packages(settings_path=config.pi.settings_path, packages=config.pi.packages)
            emit(json.dumps(result, indent=2, ensure_ascii=False))
        job = _spawn_job("升级 Pi 自定义组件", _do_pi_packages_upgrade)

    elif action == "pi_package_upgrade" and req.package:
        def _do_pi_package_upgrade(emit: Any) -> None:
            from ai_config_sync.pi_package_manager import upgrade_pi_packages
            from ai_config_sync.sync import default_paths, load_sync_config
            paths = default_paths(REPO_ROOT, None)
            config = load_sync_config(paths.config_path)
            if config.pi is None:
                raise RuntimeError("当前未配置 Pi")
            emit(f"升级 Pi 组件: {req.package}")
            result = upgrade_pi_packages(
                settings_path=config.pi.settings_path,
                packages=config.pi.packages,
                target_specs=(req.package,),
            )
            emit(json.dumps(result, indent=2, ensure_ascii=False))

        job = _spawn_job(f"升级 Pi 组件: {req.package}", _do_pi_package_upgrade)

    elif action == "sync_service_start":
        def _do_sync_start(emit: Any) -> None:
            from ai_config_sync.sync import default_paths, start_service
            emit(json.dumps(start_service(default_paths(REPO_ROOT, None), 2.0), indent=2, ensure_ascii=False))
        job = _spawn_job("启动同步服务", _do_sync_start)

    elif action == "sync_service_stop":
        def _do_sync_stop(emit: Any) -> None:
            from ai_config_sync.sync import default_paths, stop_service
            emit(json.dumps(stop_service(default_paths(REPO_ROOT, None)), indent=2, ensure_ascii=False))
        job = _spawn_job("停止同步服务", _do_sync_stop)

    else:
        raise HTTPException(400, f"未知操作: {action}")

    return {"id": job.id, "label": job.label}


@app.get("/api/jobs/{job_id}/events")
async def api_job_events(job_id: str) -> StreamingResponse:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")

    async def _generate():
        for line in list(job.lines):
            yield f"data: {json.dumps({'line': line})}\n\n"
        if job.status != "running":
            yield f"data: {json.dumps({'done': True, 'status': job.status})}\n\n"
            return
        loop = asyncio.get_event_loop()
        while True:
            try:
                msg = await asyncio.wait_for(
                    loop.run_in_executor(None, job.q.get, True, 30), timeout=35)
                if msg is None:
                    yield f"data: {json.dumps({'done': True, 'status': job.status})}\n\n"
                    break
                yield f"data: {json.dumps({'line': msg})}\n\n"
            except (asyncio.TimeoutError, Exception):
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class McpAddBody(BaseModel):
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = []
    url: str | None = None


@app.post("/api/mcp")
async def api_mcp_add(body: McpAddBody) -> dict[str, Any]:
    def _add(emit: Any) -> None:
        from ai_config_sync.sync import McpServerConfig, default_paths, add_mcp_server, load_sync_config, sync_clients
        from ai_config_sync.mcp_runtime import preflight_mcp
        paths = default_paths(REPO_ROOT, None)
        emit(f"添加 MCP 服务器: {body.name}")
        add_mcp_server(paths.config_path, McpServerConfig(
            name=body.name, transport=body.transport,
            command=body.command, args=tuple(body.args), url=body.url))
        preflight_mcp(REPO_ROOT)
        emit(json.dumps(sync_clients(load_sync_config(paths.config_path), paths.state_path), indent=2, ensure_ascii=False))
    return {"id": (job := _spawn_job(f"添加 MCP: {body.name}", _add)).id, "label": job.label}


@app.delete("/api/mcp/{name}")
async def api_mcp_remove(name: str) -> dict[str, Any]:
    def _remove(emit: Any) -> None:
        from ai_config_sync.sync import default_paths, remove_mcp_server, load_sync_config, sync_clients
        from ai_config_sync.mcp_runtime import preflight_mcp
        paths = default_paths(REPO_ROOT, None)
        emit(f"移除 MCP 服务器: {name}")
        remove_mcp_server(paths.config_path, name)
        preflight_mcp(REPO_ROOT)
        emit(json.dumps(sync_clients(load_sync_config(paths.config_path), paths.state_path), indent=2, ensure_ascii=False))
    return {"id": (job := _spawn_job(f"移除 MCP: {name}", _remove)).id, "label": job.label}



# ─── skill file management ────────────────────────────────────────────────────

@app.delete("/api/skills")
async def api_skill_remove(path: str = Query(...)) -> dict[str, Any]:
    p = Path(path).resolve()
    if not p.exists() or not p.is_file() or p.suffix.lower() not in {".md", ".yaml", ".yml", ".json"}:
        raise HTTPException(400, f"无效的 skill 路径: {path}")
    p.unlink()
    return {"ok": True, "deleted": str(p)}


# ─── self (dashboard daemon) ──────────────────────────────────────────────────

_SELF_SVC = "ai-config-sync-web.service"


def _user_systemctl(*args: str) -> subprocess.CompletedProcess[str]:
    return _run(["systemctl", "--user", *args], timeout=10)


def _parse_systemctl_show(stdout: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _self_service_issue(service: str) -> str | None:
    try:
        journal = _run(["journalctl", "--user", "-u", service, "-n", "20", "--no-pager"], timeout=10)
    except Exception:
        return None
    text = f"{journal.stdout}\n{journal.stderr}".lower()
    if "address already in use" in text or "errno 98" in text:
        return "port-in-use"
    return None


def _self_status_payload() -> dict[str, Any]:
    active = _user_systemctl("is-active", _SELF_SVC)
    enabled = _user_systemctl("is-enabled", _SELF_SVC)
    show = _user_systemctl("show", _SELF_SVC, "--property=ActiveState", "--property=SubState", "--property=Result", "--property=ExecMainStatus", "--property=ExecMainCode")
    show_data = _parse_systemctl_show(show.stdout)
    active_state = (show_data.get("ActiveState") or active.stdout.strip() or "unknown").strip()
    sub_state = (show_data.get("SubState") or "").strip()
    result = (show_data.get("Result") or "").strip()
    exec_main_status = (show_data.get("ExecMainStatus") or "").strip()
    issue = _self_service_issue(_SELF_SVC) if active_state in {"activating", "failed", "inactive"} else None
    if active_state == "active":
        state_label = "守护运行中"
    elif active_state == "activating":
        state_label = "守护重启中" if sub_state == "auto-restart" else "守护启动中"
    elif active_state == "failed":
        state_label = "守护启动失败"
    elif active_state == "inactive":
        state_label = "守护已停止"
    else:
        state_label = f"守护状态: {active_state}"
    return {
        "service": _SELF_SVC,
        "active": active_state,
        "enabled": enabled.stdout.strip(),
        "sub_state": sub_state,
        "result": result,
        "exec_main_status": exec_main_status,
        "issue": issue,
        "state_label": state_label,
        "can_start": active_state not in {"active", "activating"},
    }


def _find_web_server_conflicts() -> list[int]:
    conflicts: list[int] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"] or []
            if not cmdline:
                continue
            text = " ".join(cmdline).lower()
            if "ai_config_sync.cli web-server" not in text:
                continue
            if "--port 9731" not in text:
                continue
            if proc.pid == os.getpid():
                continue
            conflicts.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return sorted(set(conflicts))


@app.get("/api/self")
async def api_self_status() -> dict[str, Any]:
    return await asyncio.to_thread(_self_status_payload)


@app.post("/api/self/restart")
async def api_self_restart() -> dict[str, Any]:
    threading.Thread(target=lambda: (time.sleep(0.4), _user_systemctl("restart", _SELF_SVC)), daemon=True).start()
    return {"ok": True}


@app.post("/api/self/stop")
async def api_self_stop() -> dict[str, Any]:
    threading.Thread(target=lambda: (time.sleep(0.4), _user_systemctl("stop", _SELF_SVC)), daemon=True).start()
    return {"ok": True}


@app.post("/api/self/start")
async def api_self_start() -> dict[str, Any]:
    conflicts = await asyncio.to_thread(_find_web_server_conflicts)
    if conflicts:
        await asyncio.to_thread(_terminate_process_tree, conflicts)
    r = await asyncio.to_thread(_user_systemctl, "start", _SELF_SVC)
    payload = await asyncio.to_thread(_self_status_payload)
    payload.update({"ok": r.returncode == 0, "cleared_conflicts": conflicts})
    return payload


# ─── entrypoint ───────────────────────────────────────────────────────────────

def serve(*, host: str = "0.0.0.0", port: int = 9731) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
