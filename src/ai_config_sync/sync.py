from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_config_sync.errors import SyncError
from ai_config_sync.pi_package_manager import sync_pi_packages

MANAGED_BLOCK_BEGIN = "# >>> ai-config-sync managed mcp begin"
MANAGED_BLOCK_END = "# <<< ai-config-sync managed mcp end"
SKILL_MANIFEST_NAME = ".ai-config-sync-managed.json"


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
    direct_tools: bool | tuple[str, ...] | None = None
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
    skill_roots: tuple[SkillRootConfig, ...] = ()
    mcp_servers: tuple[McpServerConfig, ...] = ()
    global_prompt_path: Path | None = None
    global_prompt_append_path: Path | None = None


@dataclass(frozen=True)
class ClaudeTargetConfig:
    config_path: Path
    skills_dir: Path
    skill_roots: tuple[SkillRootConfig, ...] = ()
    mcp_servers: tuple[McpServerConfig, ...] = ()
    global_prompt_path: Path | None = None
    global_prompt_append_path: Path | None = None


@dataclass(frozen=True)
class OpencodeTargetConfig:
    config_path: Path
    agent_prefix: str = "skill-"
    skill_roots: tuple[SkillRootConfig, ...] = ()
    mcp_servers: tuple[McpServerConfig, ...] = ()
    global_prompt_path: Path | None = None
    global_prompt_append_path: Path | None = None


@dataclass(frozen=True)
class PiTargetConfig:
    settings_path: Path
    mcp_config_path: Path
    models_path: Path
    skills_dir: Path
    fallback_chains_path: Path
    context_prune_settings_path: Path
    skill_roots: tuple[SkillRootConfig, ...] = ()
    mcp_servers: tuple[McpServerConfig, ...] = ()
    packages: tuple[str, ...] = ("npm:pi-mcp-adapter",)
    mcp_settings: dict[str, Any] | None = None
    providers: dict[str, Any] | None = None
    fallback_chains: dict[str, list[str]] | None = None
    context_prune_settings: dict[str, Any] | None = None
    default_provider: str | None = None
    default_model: str | None = None
    enable_skill_commands: bool | None = None
    global_prompt_path: Path | None = None
    global_prompt_append_path: Path | None = None


@dataclass(frozen=True)
class SyncConfig:
    mcp_servers: tuple[McpServerConfig, ...]
    skill_roots: tuple[SkillRootConfig, ...]
    include: tuple[str, ...]
    global_prompt_path: Path | None
    codex: CodexTargetConfig | None
    claude: ClaudeTargetConfig | None
    opencode: OpencodeTargetConfig | None
    pi: PiTargetConfig | None


@dataclass(frozen=True)
class ResolvedSkill:
    name: str
    source_dir: Path
    skill_file: Path
    prompt: str
    description: str


@dataclass(frozen=True)
class SkillLinkPlan:
    target_dir: Path
    linked: tuple[str, ...]
    removed: tuple[str, ...]
    paths_to_remove: tuple[Path, ...]
    symlinks_to_create: tuple[tuple[Path, Path], ...]


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
    config_path = path.expanduser().resolve()
    repo_root = config_path.parent
    data = json.loads(config_path.read_text(encoding="utf-8"))
    roots = _parse_skill_roots(data.get("skillRoots", []), repo_root)
    mcp_servers = _parse_mcp_servers(data.get("mcpServers", {}), repo_root)
    targets = data.get("targets", {})
    codex = CodexTargetConfig(
        config_path=_resolve_path(targets["codex"]["configPath"], repo_root),
        skills_dir=_resolve_path(targets["codex"]["skillsDir"], repo_root),
        skill_roots=_parse_skill_roots(targets["codex"].get("skillRoots", []), repo_root),
        mcp_servers=_parse_mcp_servers(targets["codex"].get("mcpServers", {}), repo_root),
        global_prompt_path=_optional_path(targets["codex"].get("globalPromptPath"), repo_root),
        global_prompt_append_path=_optional_path(targets["codex"].get("globalPromptAppendPath"), repo_root),
    ) if "codex" in targets else None
    claude = ClaudeTargetConfig(
        config_path=_resolve_path(targets["claude"]["configPath"], repo_root),
        skills_dir=_resolve_path(targets["claude"]["skillsDir"], repo_root),
        skill_roots=_parse_skill_roots(targets["claude"].get("skillRoots", []), repo_root),
        mcp_servers=_parse_mcp_servers(targets["claude"].get("mcpServers", {}), repo_root),
        global_prompt_path=_optional_path(targets["claude"].get("globalPromptPath"), repo_root),
        global_prompt_append_path=_optional_path(targets["claude"].get("globalPromptAppendPath"), repo_root),
    ) if "claude" in targets else None
    opencode = OpencodeTargetConfig(
        config_path=_resolve_path(targets["opencode"]["configPath"], repo_root),
        agent_prefix=str(targets["opencode"].get("agentPrefix", "skill-")),
        skill_roots=_parse_skill_roots(targets["opencode"].get("skillRoots", []), repo_root),
        mcp_servers=_parse_mcp_servers(targets["opencode"].get("mcpServers", {}), repo_root),
        global_prompt_path=_optional_path(targets["opencode"].get("globalPromptPath"), repo_root),
        global_prompt_append_path=_optional_path(targets["opencode"].get("globalPromptAppendPath"), repo_root),
    ) if "opencode" in targets else None
    if "pi" in targets:
        pi_settings_path = _resolve_path(targets["pi"]["settingsPath"], repo_root)
        pi = PiTargetConfig(
            settings_path=pi_settings_path,
            mcp_config_path=_resolve_path(targets["pi"]["mcpConfigPath"], repo_root),
            models_path=_optional_path(targets["pi"].get("modelsPath"), repo_root) or pi_settings_path.with_name("models.json"),
            skills_dir=_resolve_path(targets["pi"]["skillsDir"], repo_root),
            fallback_chains_path=_optional_path(targets["pi"].get("fallbackChainsPath"), repo_root)
            or pi_settings_path.parent.parent / "fallback-chains.json",
            context_prune_settings_path=_optional_path(targets["pi"].get("contextPruneSettingsPath"), repo_root)
            or pi_settings_path.parent / "context-prune" / "settings.json",
            skill_roots=_parse_skill_roots(targets["pi"].get("skillRoots", []), repo_root),
            mcp_servers=_parse_mcp_servers(targets["pi"].get("mcpServers", {}), repo_root),
            packages=tuple(str(item) for item in targets["pi"].get("packages", ["npm:pi-mcp-adapter"])),
            mcp_settings=dict(targets["pi"].get("mcpSettings", {})),
            providers=dict(targets["pi"].get("providers", {})),
            fallback_chains=_parse_string_list_mapping(targets["pi"].get("fallbackChains", {})),
            context_prune_settings=dict(targets["pi"].get("contextPruneSettings", {})),
            default_provider=targets["pi"].get("defaultProvider"),
            default_model=targets["pi"].get("defaultModel"),
            enable_skill_commands=targets["pi"].get("enableSkillCommands"),
            global_prompt_path=_optional_path(targets["pi"].get("globalPromptPath"), repo_root),
            global_prompt_append_path=_optional_path(targets["pi"].get("globalPromptAppendPath"), repo_root),
        )
    else:
        pi = None
    return SyncConfig(
        mcp_servers=mcp_servers,
        skill_roots=roots,
        include=tuple(data.get("include", ["*"])),
        global_prompt_path=_optional_path(data.get("globalPromptPath"), repo_root),
        codex=codex,
        claude=claude,
        opencode=opencode,
        pi=pi,
    )


def sync_clients(config: SyncConfig, state_path: Path) -> dict[str, Any]:
    _validate_included_skill_names(config)
    previous = _load_state(state_path)
    previous_claude_mcp = previous.get("claude", {}).get("mcp", [])
    previous_codex_mcp = previous.get("codex", {}).get("mcp", [])
    previous_opencode_mcp = previous.get("opencode", {}).get("mcp", [])
    previous_pi_mcp = previous.get("pi", {}).get("mcp", [])
    previous_codex_skills = previous.get("codex", {}).get("skills", [])
    previous_claude_skills = previous.get("claude", {}).get("skills", [])
    previous_opencode_agents = previous.get("opencode", {}).get("agents", [])
    previous_pi_skills = previous.get("pi", {}).get("skills", [])
    previous_pi_packages = previous.get("pi", {}).get("packages", [])
    previous_pi_providers = previous.get("pi", {}).get("providers", [])
    previous_codex_prompt_path = _optional_path(previous.get("codex", {}).get("global_prompt_path"))
    previous_claude_prompt_path = _optional_path(previous.get("claude", {}).get("global_prompt_path"))
    previous_opencode_prompt_path = _optional_path(previous.get("opencode", {}).get("global_prompt_path"))
    previous_pi_prompt_path = _optional_path(previous.get("pi", {}).get("global_prompt_path"))
    previous_codex_config_path = _optional_path(previous.get("codex", {}).get("config_path"))
    previous_claude_config_path = _optional_path(previous.get("claude", {}).get("config_path"))
    previous_opencode_config_path = _optional_path(previous.get("opencode", {}).get("config_path"))
    previous_pi_settings_path = _optional_path(previous.get("pi", {}).get("settings_path"))
    previous_pi_mcp_config_path = _optional_path(previous.get("pi", {}).get("mcp_config_path"))
    previous_pi_models_path = _optional_path(previous.get("pi", {}).get("models_path"))
    previous_pi_fallback_chains_path = _optional_path(previous.get("pi", {}).get("fallback_chains_path"))
    previous_pi_context_prune_settings_path = _optional_path(previous.get("pi", {}).get("context_prune_settings_path"))
    previous_codex_skills_dir = _optional_path(previous.get("codex", {}).get("skills_dir"))
    previous_claude_skills_dir = _optional_path(previous.get("claude", {}).get("skills_dir"))
    previous_pi_skills_dir = _optional_path(previous.get("pi", {}).get("skills_dir"))
    previous_pi_default_provider = previous.get("pi", {}).get("default_provider")
    previous_pi_default_model = previous.get("pi", {}).get("default_model")
    previous_pi_enable_skill_commands = previous.get("pi", {}).get("enable_skill_commands")
    previous_pi_mcp_setting_keys = _normalize_string_list(previous.get("pi", {}).get("mcp_setting_keys"))
    codex_legacy_paths = _legacy_default_target_paths("codex")
    claude_legacy_paths = _legacy_default_target_paths("claude")
    opencode_legacy_paths = _legacy_default_target_paths("opencode")
    if previous_codex_config_path is None:
        previous_codex_config_path = _infer_legacy_config_path(
            codex_legacy_paths["config_path"],
            previous_codex_mcp,
        )
    if previous_claude_config_path is None:
        previous_claude_config_path = _infer_legacy_config_path(
            claude_legacy_paths["config_path"],
            previous_claude_mcp,
        )
    if previous_opencode_config_path is None:
        previous_opencode_config_path = _infer_legacy_config_path(
            opencode_legacy_paths["config_path"],
            [*previous_opencode_mcp, *previous_opencode_agents],
        )
    if previous_codex_skills_dir is None and previous_codex_config_path is not None:
        previous_codex_skills_dir = _infer_legacy_skills_dir(
            previous_codex_config_path,
            previous_codex_skills,
            ("skills-shared", "skills"),
        )
    if previous_codex_skills_dir is None:
        previous_codex_skills_dir = _infer_legacy_skills_dir_from_candidates(
            previous_codex_skills,
            codex_legacy_paths["skills_dirs"],
        )
    if previous_claude_skills_dir is None and previous_claude_config_path is not None:
        previous_claude_skills_dir = _infer_legacy_skills_dir(
            previous_claude_config_path,
            previous_claude_skills,
            ("skills",),
        )
    if previous_claude_skills_dir is None:
        previous_claude_skills_dir = _infer_legacy_skills_dir_from_candidates(
            previous_claude_skills,
            claude_legacy_paths["skills_dirs"],
        )

    shared_skills = resolve_skills(config.skill_roots, config.include, allow_missing=True)
    enabled_servers = tuple(server for server in config.mcp_servers if server.enabled)
    result: dict[str, Any] = {
        "mcp_servers": [server.name for server in enabled_servers],
        "skills": [skill.name for skill in shared_skills],
        "targets": {},
    }

    codex_state: dict[str, Any] = {}
    claude_state: dict[str, Any] = {}
    opencode_state: dict[str, Any] = {}
    pi_state: dict[str, Any] = {}
    codex_config_payload: tuple[Path, str] | None = None
    claude_config_payload: tuple[Path, str] | None = None
    opencode_config_payload: tuple[Path, str] | None = None
    pi_settings_payload: tuple[Path, str] | None = None
    pi_mcp_config_payload: tuple[Path, str] | None = None
    pi_models_payload: tuple[Path, str] | None = None
    pi_extra_json_payloads: list[tuple[Path, str]] = []
    codex_skill_plan: SkillLinkPlan | None = None
    claude_skill_plan: SkillLinkPlan | None = None
    pi_skill_plan: SkillLinkPlan | None = None
    pi_package_sync_result: dict[str, Any] | None = None
    codex_prompt_text: str | None = None
    claude_prompt_text: str | None = None
    opencode_prompt_text: str | None = None
    pi_prompt_text: str | None = None
    active_codex_prompt_path: Path | None = None
    active_claude_prompt_path: Path | None = None
    active_opencode_prompt_path: Path | None = None
    active_pi_prompt_path: Path | None = None

    if config.codex:
        codex_skills = resolve_skills(config.skill_roots + config.codex.skill_roots, config.include, allow_missing=True)
        codex_servers = _merge_mcp_servers(enabled_servers, config.codex.mcp_servers)
        codex_original = config.codex.config_path.read_text(encoding="utf-8") if config.codex.config_path.exists() else ""
        codex_config_payload = (
            config.codex.config_path,
            build_codex_config_payload(codex_original, codex_servers, previous_codex_mcp),
        )
        codex_skill_plan = plan_skill_links(config.codex.skills_dir, codex_skills, previous_codex_skills)
        codex_result: dict[str, Any] = {
            "config_path": str(config.codex.config_path),
            "skills": {"linked": list(codex_skill_plan.linked), "removed": list(codex_skill_plan.removed)},
        }
        codex_prompt_text = build_global_prompt(config.global_prompt_path, config.codex.global_prompt_append_path)
        if codex_prompt_text is not None and config.codex.global_prompt_path is not None:
            codex_result["global_prompt_path"] = str(config.codex.global_prompt_path)
            active_codex_prompt_path = config.codex.global_prompt_path
            if config.codex.global_prompt_append_path is not None:
                codex_result["global_prompt_append_path"] = str(config.codex.global_prompt_append_path)
        result["targets"]["codex"] = codex_result
        codex_state = {
            "config_path": str(config.codex.config_path),
            "skills_dir": str(config.codex.skills_dir),
            "mcp": [server.name for server in codex_servers],
            "skills": [skill.name for skill in codex_skills],
            "global_prompt_path": str(active_codex_prompt_path) if active_codex_prompt_path is not None else None,
            "global_prompt_append_path": str(config.codex.global_prompt_append_path)
            if active_codex_prompt_path is not None and config.codex.global_prompt_append_path is not None
            else None,
        }
    elif previous_codex_config_path is not None:
        codex_original = previous_codex_config_path.read_text(encoding="utf-8") if previous_codex_config_path.exists() else ""
        codex_config_payload = (
            previous_codex_config_path,
            build_codex_config_payload(codex_original, (), previous_codex_mcp),
        )
        if previous_codex_skills_dir is not None:
            codex_skill_plan = plan_skill_links(previous_codex_skills_dir, [], previous_codex_skills)

    if config.claude:
        claude_skills = resolve_skills(config.skill_roots + config.claude.skill_roots, config.include, allow_missing=True)
        claude_servers = _merge_mcp_servers(enabled_servers, config.claude.mcp_servers)
        claude_original = config.claude.config_path.read_text(encoding="utf-8") if config.claude.config_path.exists() else ""
        claude_config_payload = (
            config.claude.config_path,
            build_claude_config_payload(claude_original, claude_servers, previous_claude_mcp),
        )
        claude_skill_plan = plan_skill_links(config.claude.skills_dir, claude_skills, previous_claude_skills)
        claude_result: dict[str, Any] = {
            "config_path": str(config.claude.config_path),
            "skills": {"linked": list(claude_skill_plan.linked), "removed": list(claude_skill_plan.removed)},
        }
        claude_prompt_text = build_global_prompt(config.global_prompt_path, config.claude.global_prompt_append_path)
        if claude_prompt_text is not None and config.claude.global_prompt_path is not None:
            claude_result["global_prompt_path"] = str(config.claude.global_prompt_path)
            active_claude_prompt_path = config.claude.global_prompt_path
            if config.claude.global_prompt_append_path is not None:
                claude_result["global_prompt_append_path"] = str(config.claude.global_prompt_append_path)
        result["targets"]["claude"] = claude_result
        claude_state = {
            "config_path": str(config.claude.config_path),
            "skills_dir": str(config.claude.skills_dir),
            "mcp": [server.name for server in claude_servers],
            "skills": [skill.name for skill in claude_skills],
            "global_prompt_path": str(active_claude_prompt_path) if active_claude_prompt_path is not None else None,
            "global_prompt_append_path": str(config.claude.global_prompt_append_path)
            if active_claude_prompt_path is not None and config.claude.global_prompt_append_path is not None
            else None,
        }
    elif previous_claude_config_path is not None:
        claude_original = previous_claude_config_path.read_text(encoding="utf-8") if previous_claude_config_path.exists() else ""
        claude_config_payload = (
            previous_claude_config_path,
            build_claude_config_payload(claude_original, (), previous_claude_mcp),
        )
        if previous_claude_skills_dir is not None:
            claude_skill_plan = plan_skill_links(previous_claude_skills_dir, [], previous_claude_skills)

    if config.opencode:
        opencode_skills = resolve_skills(config.skill_roots + config.opencode.skill_roots, config.include, allow_missing=True)
        opencode_servers = _merge_mcp_servers(enabled_servers, config.opencode.mcp_servers)
        opencode_original = config.opencode.config_path.read_text(encoding="utf-8") if config.opencode.config_path.exists() else ""
        opencode_config_payload = (
            config.opencode.config_path,
            build_opencode_config_payload(
                opencode_original,
                opencode_servers,
                opencode_skills,
                config.opencode.agent_prefix,
                previous_opencode_mcp,
                previous_opencode_agents,
            ),
        )
        opencode_result: dict[str, Any] = {
            "config_path": str(config.opencode.config_path),
            "agents": [f"{config.opencode.agent_prefix}{skill.name}" for skill in opencode_skills],
        }
        opencode_prompt_text = build_global_prompt(config.global_prompt_path, config.opencode.global_prompt_append_path)
        if opencode_prompt_text is not None and config.opencode.global_prompt_path is not None:
            opencode_result["global_prompt_path"] = str(config.opencode.global_prompt_path)
            active_opencode_prompt_path = config.opencode.global_prompt_path
            if config.opencode.global_prompt_append_path is not None:
                opencode_result["global_prompt_append_path"] = str(config.opencode.global_prompt_append_path)
        result["targets"]["opencode"] = opencode_result
        opencode_state = {
            "config_path": str(config.opencode.config_path),
            "agent_prefix": config.opencode.agent_prefix,
            "mcp": [server.name for server in opencode_servers],
            "agents": [f"{config.opencode.agent_prefix}{skill.name}" for skill in opencode_skills],
            "global_prompt_path": str(active_opencode_prompt_path) if active_opencode_prompt_path is not None else None,
            "global_prompt_append_path": str(config.opencode.global_prompt_append_path)
            if active_opencode_prompt_path is not None and config.opencode.global_prompt_append_path is not None
            else None,
        }
    elif previous_opencode_config_path is not None:
        opencode_original = previous_opencode_config_path.read_text(encoding="utf-8") if previous_opencode_config_path.exists() else ""
        opencode_config_payload = (
            previous_opencode_config_path,
            build_opencode_config_payload(opencode_original, (), [], "skill-", previous_opencode_mcp, previous_opencode_agents),
        )

    if config.pi:
        pi_skills = resolve_skills(config.skill_roots + config.pi.skill_roots, config.include, allow_missing=True)
        pi_servers = _merge_mcp_servers(enabled_servers, config.pi.mcp_servers)
        pi_settings_original = config.pi.settings_path.read_text(encoding="utf-8") if config.pi.settings_path.exists() else ""
        pi_settings_payload = (
            config.pi.settings_path,
            build_pi_settings_payload(
                pi_settings_original,
                (str(config.pi.skills_dir),),
                config.pi.packages,
                previous_pi_packages,
                [str(previous_pi_skills_dir)] if previous_pi_skills_dir is not None else [],
                config.pi.default_provider,
                config.pi.default_model,
                previous_pi_default_provider,
                previous_pi_default_model,
                config.pi.enable_skill_commands,
                previous_pi_enable_skill_commands,
            ),
        )
        pi_mcp_original = config.pi.mcp_config_path.read_text(encoding="utf-8") if config.pi.mcp_config_path.exists() else ""
        pi_mcp_config_payload = (
            config.pi.mcp_config_path,
            build_pi_mcp_config_payload(
                pi_mcp_original,
                pi_servers,
                previous_pi_mcp,
                config.pi.mcp_settings or {},
                previous_pi_mcp_setting_keys,
            ),
        )
        pi_models_original = config.pi.models_path.read_text(encoding="utf-8") if config.pi.models_path.exists() else ""
        pi_models_payload = (
            config.pi.models_path,
            build_pi_models_payload(pi_models_original, config.pi.providers or {}, previous_pi_providers),
        )
        pi_extra_json_payloads.append(
            (
                config.pi.fallback_chains_path,
                build_pi_fallback_chains_payload(config.pi.fallback_chains or {}),
            )
        )
        pi_extra_json_payloads.append(
            (
                config.pi.context_prune_settings_path,
                build_pi_context_prune_settings_payload(config.pi.context_prune_settings or {}),
            )
        )
        pi_skill_plan = plan_skill_links(config.pi.skills_dir, pi_skills, previous_pi_skills)
        pi_result: dict[str, Any] = {
            "settings_path": str(config.pi.settings_path),
            "mcp_config_path": str(config.pi.mcp_config_path),
            "models_path": str(config.pi.models_path),
            "fallback_chains_path": str(config.pi.fallback_chains_path),
            "context_prune_settings_path": str(config.pi.context_prune_settings_path),
            "packages": list(config.pi.packages),
            "mcp_setting_keys": sorted((config.pi.mcp_settings or {}).keys()),
            "providers": sorted((config.pi.providers or {}).keys()),
            "fallback_chains": sorted((config.pi.fallback_chains or {}).keys()),
            "context_prune_setting_keys": sorted((config.pi.context_prune_settings or {}).keys()),
            "skills": {"linked": list(pi_skill_plan.linked), "removed": list(pi_skill_plan.removed)},
        }
        if config.pi.default_provider is not None:
            pi_result["default_provider"] = config.pi.default_provider
        if config.pi.default_model is not None:
            pi_result["default_model"] = config.pi.default_model
        if config.pi.enable_skill_commands is not None:
            pi_result["enable_skill_commands"] = config.pi.enable_skill_commands
        pi_prompt_text = build_global_prompt(config.global_prompt_path, config.pi.global_prompt_append_path)
        if pi_prompt_text is not None and config.pi.global_prompt_path is not None:
            pi_result["global_prompt_path"] = str(config.pi.global_prompt_path)
            active_pi_prompt_path = config.pi.global_prompt_path
            if config.pi.global_prompt_append_path is not None:
                pi_result["global_prompt_append_path"] = str(config.pi.global_prompt_append_path)
        result["targets"]["pi"] = pi_result
        pi_state = {
            "settings_path": str(config.pi.settings_path),
            "mcp_config_path": str(config.pi.mcp_config_path),
            "models_path": str(config.pi.models_path),
            "fallback_chains_path": str(config.pi.fallback_chains_path),
            "context_prune_settings_path": str(config.pi.context_prune_settings_path),
            "skills_dir": str(config.pi.skills_dir),
            "packages": list(config.pi.packages),
            "mcp_setting_keys": sorted((config.pi.mcp_settings or {}).keys()),
            "providers": sorted((config.pi.providers or {}).keys()),
            "fallback_chain_names": sorted((config.pi.fallback_chains or {}).keys()),
            "context_prune_setting_keys": sorted((config.pi.context_prune_settings or {}).keys()),
            "default_provider": config.pi.default_provider,
            "default_model": config.pi.default_model,
            "enable_skill_commands": config.pi.enable_skill_commands,
            "mcp": [server.name for server in pi_servers],
            "skills": [skill.name for skill in pi_skills],
            "global_prompt_path": str(active_pi_prompt_path) if active_pi_prompt_path is not None else None,
            "global_prompt_append_path": str(config.pi.global_prompt_append_path)
            if active_pi_prompt_path is not None and config.pi.global_prompt_append_path is not None
            else None,
        }
    elif (
        previous_pi_settings_path is not None
        or previous_pi_mcp_config_path is not None
        or previous_pi_models_path is not None
    ):
        if previous_pi_settings_path is not None:
            pi_settings_original = previous_pi_settings_path.read_text(encoding="utf-8") if previous_pi_settings_path.exists() else ""
            pi_settings_payload = (
                previous_pi_settings_path,
                build_pi_settings_payload(
                    pi_settings_original,
                    (),
                    (),
                    previous_pi_packages,
                    [str(previous_pi_skills_dir)] if previous_pi_skills_dir is not None else [],
                    None,
                    None,
                    previous_pi_default_provider,
                    previous_pi_default_model,
                    None,
                    previous_pi_enable_skill_commands,
                ),
            )
        if previous_pi_mcp_config_path is not None:
            pi_mcp_original = previous_pi_mcp_config_path.read_text(encoding="utf-8") if previous_pi_mcp_config_path.exists() else ""
            pi_mcp_config_payload = (
                previous_pi_mcp_config_path,
                build_pi_mcp_config_payload(pi_mcp_original, (), previous_pi_mcp, {}, previous_pi_mcp_setting_keys),
            )
        if previous_pi_models_path is not None:
            pi_models_original = previous_pi_models_path.read_text(encoding="utf-8") if previous_pi_models_path.exists() else ""
            pi_models_payload = (
                previous_pi_models_path,
                build_pi_models_payload(pi_models_original, {}, previous_pi_providers),
            )
        if previous_pi_skills_dir is not None:
            pi_skill_plan = plan_skill_links(previous_pi_skills_dir, [], previous_pi_skills)

    if config.pi is not None:
        pi_package_sync_result = sync_pi_packages(
            settings_path=config.pi.settings_path,
            packages=config.pi.packages,
            previous_packages=previous_pi_packages,
        )
        result["targets"]["pi"]["package_sync"] = pi_package_sync_result
    elif previous_pi_settings_path is not None and previous_pi_packages:
        sync_pi_packages(
            settings_path=previous_pi_settings_path,
            packages=(),
            previous_packages=previous_pi_packages,
        )

    if codex_config_payload is not None:
        _atomic_write_text(*codex_config_payload)
    if claude_config_payload is not None:
        _atomic_write_text(*claude_config_payload)
    if opencode_config_payload is not None:
        _atomic_write_text(*opencode_config_payload)
    if pi_mcp_config_payload is not None:
        _atomic_write_text(*pi_mcp_config_payload)
    if pi_models_payload is not None:
        _atomic_write_text(*pi_models_payload)
    for payload in pi_extra_json_payloads:
        _atomic_write_text(*payload)
    if pi_settings_payload is not None:
        _atomic_write_text(*pi_settings_payload)
    if codex_skill_plan is not None:
        apply_skill_link_plan(codex_skill_plan)
    if claude_skill_plan is not None:
        apply_skill_link_plan(claude_skill_plan)
    if pi_skill_plan is not None:
        apply_skill_link_plan(pi_skill_plan)
    if codex_prompt_text is not None and active_codex_prompt_path is not None:
        sync_global_prompt(active_codex_prompt_path, codex_prompt_text)
    _cleanup_previous_output_path(previous_codex_prompt_path, active_codex_prompt_path)
    if claude_prompt_text is not None and active_claude_prompt_path is not None:
        sync_global_prompt(active_claude_prompt_path, claude_prompt_text)
    _cleanup_previous_output_path(previous_claude_prompt_path, active_claude_prompt_path)
    if opencode_prompt_text is not None and active_opencode_prompt_path is not None:
        sync_global_prompt(active_opencode_prompt_path, opencode_prompt_text)
    _cleanup_previous_output_path(previous_opencode_prompt_path, active_opencode_prompt_path)
    if pi_prompt_text is not None and active_pi_prompt_path is not None:
        sync_global_prompt(active_pi_prompt_path, pi_prompt_text)
    _cleanup_previous_output_path(previous_pi_prompt_path, active_pi_prompt_path)
    _cleanup_previous_output_path(
        previous_pi_fallback_chains_path,
        config.pi.fallback_chains_path if config.pi is not None else None,
    )
    _cleanup_previous_output_path(
        previous_pi_context_prune_settings_path,
        config.pi.context_prune_settings_path if config.pi is not None else None,
    )

    state = {
        "codex": codex_state,
        "claude": claude_state,
        "opencode": opencode_state,
        "pi": pi_state,
        "last_synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write_text(state_path, json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    return result


def watch_loop(paths: SyncPaths, interval_seconds: float) -> None:
    from ai_config_sync.mcp_runtime import preflight_mcp, reap_mcp

    try:
        reap_mcp(paths.repo_root)  # clean stale orphans on startup
    except Exception:
        pass  # serena manager may not be bootstrapped yet
    last_fingerprint: str | None = None
    reap_counter = 0
    reap_interval_cycles = max(1, int(300 / interval_seconds)) if interval_seconds > 0 else 0
    while True:
        fingerprint: str | None = None
        try:
            fingerprint = compute_fingerprint(paths.config_path)
            if fingerprint != last_fingerprint:
                config = load_sync_config(paths.config_path)
                preflight_mcp(paths.repo_root)
                result = sync_clients(config, paths.state_path)
                result["watch_fingerprint"] = fingerprint
                print(json.dumps(result, ensure_ascii=False), flush=True)
                last_fingerprint = fingerprint
            reap_counter += 1
            if reap_interval_cycles > 0 and reap_counter >= reap_interval_cycles:
                reap_counter = 0
                try:
                    reap_result = reap_mcp(paths.repo_root)
                    if reap_result.get("cleaned_idle") or reap_result.get("cleaned_unhealthy"):
                        print(
                            json.dumps({"mcp_reap": reap_result}, ensure_ascii=False),
                            flush=True,
                        )
                except Exception:
                    pass
        except Exception as exc:
            error = {"error": str(exc), "error_type": type(exc).__name__}
            if fingerprint is not None:
                error["watch_fingerprint"] = fingerprint
            print(json.dumps(error, ensure_ascii=False), flush=True)
        time.sleep(interval_seconds)


def compute_fingerprint(config_path: Path) -> str:
    repo_root = config_path.expanduser().resolve().parent
    digest = hashlib.sha256()
    digest.update(config_path.read_bytes())
    config = load_sync_config(config_path)
    _validate_included_skill_names(config)
    if config.global_prompt_path is not None:
        digest.update(config.global_prompt_path.read_bytes())
    for overlay_path in (
        config.codex.global_prompt_append_path if config.codex else None,
        config.claude.global_prompt_append_path if config.claude else None,
        config.opencode.global_prompt_append_path if config.opencode else None,
        config.pi.global_prompt_append_path if config.pi else None,
    ):
        if overlay_path is not None:
            digest.update(overlay_path.read_bytes())
    for skill in resolve_skills(_all_skill_roots(config), config.include, allow_missing=True):
        digest.update(skill.skill_file.read_bytes())
    for runtime_path in _managed_mcp_runtime_source_paths(repo_root):
        if runtime_path.is_file():
            digest.update(str(runtime_path.relative_to(repo_root)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(runtime_path.read_bytes())
    return digest.hexdigest()


def _managed_mcp_runtime_source_paths(repo_root: Path) -> tuple[Path, ...]:
    serena_manager_root = repo_root / "vendor" / "mcp" / "serena-manager"
    return tuple(
        path
        for path in [
            repo_root / "toolchain.lock.json",
            repo_root / "tools" / "mcp" / "shared" / "common.sh",
            repo_root / "tools" / "mcp" / "shared" / "serena-manager.sh",
            repo_root / "tools" / "mcp" / "shared" / "serena-agent.sh",
            repo_root / "tools" / "mcp" / "shared" / "fetch.sh",
            repo_root / "tools" / "mcp" / "shared" / "codegraph.sh",
            repo_root / "tools" / "mcp" / "shared" / "node-repl-linux.sh",
            repo_root / "vendor" / "mcp" / "serena-agent" / "requirements.lock",
            repo_root / "vendor" / "mcp" / "serena-agent" / "runner.py",
            repo_root / "vendor" / "mcp" / "fetch" / "requirements.lock",
            repo_root / "vendor" / "mcp" / "codegraph" / "package-lock.json",
            repo_root / "vendor" / "mcp" / "node-repl-linux" / "package-lock.json",
            serena_manager_root / "pyproject.toml",
            serena_manager_root / "uv.lock",
            *sorted((serena_manager_root / "src" / "serena_manager").rglob("*.py")),
        ]
        if path.exists()
    )


def resolve_skills(
    roots: tuple[SkillRootConfig, ...],
    include: tuple[str, ...],
    *,
    allow_missing: bool = False,
) -> list[ResolvedSkill]:
    discovered = discover_skills(roots)
    if not include or include == ("*",):
        names = sorted(discovered.keys())
    elif allow_missing:
        names = [name for name in include if name in discovered]
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


def _all_skill_roots(config: SyncConfig) -> tuple[SkillRootConfig, ...]:
    roots = list(config.skill_roots)
    if config.codex:
        roots.extend(config.codex.skill_roots)
    if config.claude:
        roots.extend(config.claude.skill_roots)
    if config.opencode:
        roots.extend(config.opencode.skill_roots)
    if config.pi:
        roots.extend(config.pi.skill_roots)
    return tuple(roots)


def _validate_included_skill_names(config: SyncConfig) -> None:
    if not config.include or config.include == ("*",):
        return
    discovered = discover_skills(_all_skill_roots(config))
    missing = [name for name in config.include if name not in discovered]
    if missing:
        missing_names = ", ".join(sorted(dict.fromkeys(missing)))
        raise SyncError(f"Configured include skills were not found in any managed skill root: {missing_names}")


def _merge_mcp_servers(
    shared_servers: tuple[McpServerConfig, ...],
    target_servers: tuple[McpServerConfig, ...],
) -> tuple[McpServerConfig, ...]:
    merged: dict[str, McpServerConfig] = {server.name: server for server in shared_servers}
    for server in target_servers:
        merged[server.name] = server
    return tuple(server for server in merged.values() if server.enabled)


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


def _parse_skill_roots(items: list[dict[str, Any]] | tuple[dict[str, Any], ...], repo_root: Path) -> tuple[SkillRootConfig, ...]:
    return tuple(
        SkillRootConfig(
            path=_resolve_path(item["path"], repo_root),
            prefix=str(item.get("prefix", "")),
            exclude=tuple(item.get("exclude", [])),
        )
        for item in items
    )


def _parse_mcp_servers(items: dict[str, Any], repo_root: Path) -> tuple[McpServerConfig, ...]:
    return tuple(_parse_mcp_server(name, item, repo_root) for name, item in items.items())


def plan_skill_links(target_dir: Path, skills: list[ResolvedSkill], previous_names: list[str]) -> SkillLinkPlan:
    current = {skill.name: skill for skill in skills}
    removed_names: list[str] = []
    linked_names: list[str] = []
    paths_to_remove: list[Path] = []
    symlinks_to_create: list[tuple[Path, Path]] = []
    managed_names = set(previous_names) | set(_load_skill_manifest(target_dir))
    for name in sorted(managed_names):
        if name in current:
            continue
        path = target_dir / name
        if path.is_symlink() or path.is_file():
            paths_to_remove.append(path)
            removed_names.append(name)
    for skill in skills:
        path = target_dir / skill.name
        if path.is_symlink() and path.resolve() == skill.source_dir.resolve():
            linked_names.append(skill.name)
            continue
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                paths_to_remove.append(path)
            elif path.is_dir() and skill.name in managed_names:
                paths_to_remove.append(path)
            else:
                raise SyncError(f"Refusing to overwrite non-symlink skill path: {path}")
        symlinks_to_create.append((path, skill.source_dir))
        linked_names.append(skill.name)
    return SkillLinkPlan(
        target_dir=target_dir,
        linked=tuple(linked_names),
        removed=tuple(removed_names),
        paths_to_remove=tuple(dict.fromkeys(paths_to_remove)),
        symlinks_to_create=tuple(symlinks_to_create),
    )


def apply_skill_link_plan(plan: SkillLinkPlan) -> dict[str, list[str]]:
    plan.target_dir.mkdir(parents=True, exist_ok=True)
    for path in plan.paths_to_remove:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)
    for path, source_dir in plan.symlinks_to_create:
        path.symlink_to(source_dir, target_is_directory=True)
    _write_skill_manifest(plan.target_dir, list(plan.linked))
    return {"linked": list(plan.linked), "removed": list(plan.removed)}


def sync_skill_links(target_dir: Path, skills: list[ResolvedSkill], previous_names: list[str]) -> dict[str, list[str]]:
    return apply_skill_link_plan(plan_skill_links(target_dir, skills, previous_names))


def sync_global_prompt(target_path: Path, prompt: str) -> None:
    _atomic_write_text(target_path, prompt)


def _cleanup_previous_output_path(previous_path: Path | None, current_path: Path | None) -> None:
    if previous_path is None:
        return
    previous_write_target = _output_write_target(previous_path)
    current_write_target = _output_write_target(current_path) if current_path is not None else None
    if current_path is not None and (
        previous_path == current_path or previous_write_target == current_write_target
    ):
        return
    if previous_write_target.is_symlink() or previous_write_target.is_file():
        previous_write_target.unlink(missing_ok=True)
    if previous_path != previous_write_target and (previous_path.is_symlink() or previous_path.is_file()):
        previous_path.unlink(missing_ok=True)


def build_global_prompt(base_path: Path | None, append_path: Path | None) -> str | None:
    parts: list[str] = []
    has_source = False
    if base_path is not None:
        has_source = True
        base_text = base_path.read_text(encoding="utf-8").rstrip()
        if base_text:
            parts.append(base_text)
    if append_path is not None:
        has_source = True
        append_text = append_path.read_text(encoding="utf-8").rstrip()
        if append_text:
            parts.append(append_text)
    if not has_source:
        return None
    if not parts:
        return "\n"
    return "\n\n".join(parts) + "\n"


def build_codex_config_payload(original: str, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> str:
    cleaned = _strip_managed_block(original)
    for name in previous_names:
        cleaned = _strip_named_codex_section(cleaned, name)
    managed = _render_codex_block(servers)
    return f"{cleaned.rstrip()}\n\n{managed}\n" if cleaned.strip() else f"{managed}\n"


def sync_codex_config(config_path: Path, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> None:
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    _atomic_write_text(config_path, build_codex_config_payload(original, servers, previous_names))


def build_claude_config_payload(original: str, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> str:
    data = json.loads(original) if original.strip() else {}
    current = dict(data.get("mcpServers", {}))
    for name in previous_names:
        current.pop(name, None)
    for server in servers:
        current[server.name] = _render_claude_server(server)
    data["mcpServers"] = current
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def sync_claude_config(config_path: Path, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> None:
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    _atomic_write_text(config_path, build_claude_config_payload(original, servers, previous_names))


def sync_opencode_config(
    config_path: Path,
    servers: tuple[McpServerConfig, ...],
    skills: list[ResolvedSkill],
    agent_prefix: str,
    previous_mcp_names: list[str],
    previous_agent_names: list[str],
) -> None:
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    _atomic_write_text(
        config_path,
        build_opencode_config_payload(original, servers, skills, agent_prefix, previous_mcp_names, previous_agent_names),
    )


def sync_pi_settings(
    settings_path: Path,
    skills_dirs: tuple[str, ...],
    packages: tuple[str, ...],
    previous_packages: list[str],
    previous_skills_dirs: list[str],
    default_provider: str | None = None,
    default_model: str | None = None,
    previous_default_provider: str | None = None,
    previous_default_model: str | None = None,
    enable_skill_commands: bool | None = None,
    previous_enable_skill_commands: bool | None = None,
) -> None:
    original = settings_path.read_text(encoding="utf-8") if settings_path.exists() else ""
    _atomic_write_text(
        settings_path,
        build_pi_settings_payload(
            original,
            skills_dirs,
            packages,
            previous_packages,
            previous_skills_dirs,
            default_provider,
            default_model,
            previous_default_provider,
            previous_default_model,
            enable_skill_commands,
            previous_enable_skill_commands,
        ),
    )


def build_pi_settings_payload(
    original: str,
    skills_dirs: tuple[str, ...],
    packages: tuple[str, ...],
    previous_packages: list[str],
    previous_skills_dirs: list[str],
    default_provider: str | None = None,
    default_model: str | None = None,
    previous_default_provider: str | None = None,
    previous_default_model: str | None = None,
    enable_skill_commands: bool | None = None,
    previous_enable_skill_commands: bool | None = None,
) -> str:
    data = json.loads(original) if original.strip() else {}
    current_packages = _normalize_string_list(data.get("packages"))
    for package in previous_packages:
        current_packages = [item for item in current_packages if item != package]
    current_packages.extend(package for package in packages if package not in current_packages)

    current_skills = _normalize_string_list(data.get("skills"))
    for path in previous_skills_dirs:
        current_skills = [item for item in current_skills if item != path]
    current_skills.extend(path for path in skills_dirs if path not in current_skills)

    data["packages"] = current_packages
    data["skills"] = current_skills
    if default_provider is not None:
        data["defaultProvider"] = default_provider
    elif previous_default_provider is not None and data.get("defaultProvider") == previous_default_provider:
        data.pop("defaultProvider", None)
    if default_model is not None:
        data["defaultModel"] = default_model
    elif previous_default_model is not None and data.get("defaultModel") == previous_default_model:
        data.pop("defaultModel", None)
    if enable_skill_commands is not None:
        data["enableSkillCommands"] = enable_skill_commands
    elif previous_enable_skill_commands is not None and data.get("enableSkillCommands") == previous_enable_skill_commands:
        data.pop("enableSkillCommands", None)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def sync_pi_mcp_config(config_path: Path, servers: tuple[McpServerConfig, ...], previous_names: list[str]) -> None:
    original = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    _atomic_write_text(config_path, build_pi_mcp_config_payload(original, servers, previous_names, {}, []))


def build_pi_mcp_config_payload(
    original: str,
    servers: tuple[McpServerConfig, ...],
    previous_names: list[str],
    settings: dict[str, Any],
    previous_setting_keys: list[str],
) -> str:
    data = json.loads(original) if original.strip() else {}
    current = dict(data.get("mcpServers", {}))
    for name in previous_names:
        current.pop(name, None)
    for server in servers:
        current[server.name] = _render_standard_mcp_server(server)
    data["mcpServers"] = current

    current_settings = dict(data.get("settings", {})) if isinstance(data.get("settings"), dict) else {}
    for key in previous_setting_keys:
        current_settings.pop(key, None)
    current_settings.update(settings)
    if current_settings:
        data["settings"] = current_settings
    else:
        data.pop("settings", None)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_pi_models_payload(original: str, providers: dict[str, Any], previous_names: list[str]) -> str:
    data = json.loads(original) if original.strip() else {}
    current = dict(data.get("providers", {}))
    for name in previous_names:
        current.pop(name, None)
    for name, provider in providers.items():
        current[name] = provider
    data["providers"] = current
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def build_pi_fallback_chains_payload(chains: dict[str, list[str]]) -> str:
    # Fully managed: always written from config, never merged with existing content.
    current: dict[str, list[str]] = {}
    for name, models in chains.items():
        current[name] = [str(model) for model in models]
    return json.dumps(current, indent=2, ensure_ascii=False) + "\n"


def build_pi_context_prune_settings_payload(settings: dict[str, Any]) -> str:
    # Fully managed: always written from config, never merged with existing content.
    current: dict[str, Any] = {}
    current.update(settings)
    return json.dumps(current, indent=2, ensure_ascii=False) + "\n"


def build_opencode_config_payload(
    original: str,
    servers: tuple[McpServerConfig, ...],
    skills: list[ResolvedSkill],
    agent_prefix: str,
    previous_mcp_names: list[str],
    previous_agent_names: list[str],
) -> str:
    data = _load_jsonc_text(original)
    current_mcp = dict(data.get("mcp", {}))
    for name in previous_mcp_names:
        current_mcp.pop(name, None)
    for server in servers:
        current_mcp[server.name] = _render_opencode_server(server)

    current_agents = dict(data.get("agent", {}))
    for name in previous_agent_names:
        current_agents.pop(name, None)
    for skill in skills:
        current_agents[f"{agent_prefix}{skill.name}"] = {
            "description": skill.description,
            "mode": "subagent",
            "prompt": skill.prompt,
        }

    payload = original if original.strip() else "{\n}\n"
    payload = _upsert_jsonc_top_level_value(payload, "mcp", current_mcp)
    payload = _upsert_jsonc_top_level_value(payload, "agent", current_agents)
    if not payload.endswith("\n"):
        payload += "\n"
    return payload


def add_mcp_server(config_path: Path, server: McpServerConfig) -> dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    current = dict(data.get("mcpServers", {}))
    current[server.name] = _render_source_server(server)
    data["mcpServers"] = current
    _atomic_write_text(config_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return {"added": server.name}


def remove_mcp_server(config_path: Path, name: str) -> dict[str, Any]:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    current = dict(data.get("mcpServers", {}))
    existed = name in current
    current.pop(name, None)
    data["mcpServers"] = current
    _atomic_write_text(config_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return {"removed": existed, "name": name}


def install_service(paths: SyncPaths, interval_seconds: float) -> dict[str, Any]:
    cli_path = paths.repo_root / ".venv" / "bin" / "ai-config-sync"
    exec_start = " ".join(
        [
            _systemd_quote(str(cli_path)),
            "sync-watch",
            "--config",
            _systemd_quote(str(paths.config_path)),
            "--interval",
            str(interval_seconds),
        ]
    )
    content = (
        "[Unit]\n"
        "Description=AI config sync watch\n"
        "After=default.target\n\n"
        "[Service]\n"
        "Type=simple\n"
        f"WorkingDirectory={paths.repo_root}\n"
        f"ExecStart={exec_start}\n"
        "Restart=always\n"
        "RestartSec=2\n\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )
    _atomic_write_text(paths.service_path, content)
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


def _parse_mcp_server(name: str, item: dict[str, Any], repo_root: Path) -> McpServerConfig:
    return McpServerConfig(
        name=name,
        transport=str(item.get("type", "stdio")),
        command=_optional_string(item.get("command"), repo_root),
        args=tuple(_expand_string_template(str(arg), repo_root) for arg in item.get("args", [])),
        cwd=_optional_string(item.get("cwd"), repo_root),
        env={str(k): _expand_string_template(str(v), repo_root) for k, v in item.get("env", {}).items()} or None,
        url=item.get("url"),
        headers={str(k): str(v) for k, v in item.get("headers", {}).items()} or None,
        tool_timeout_sec=int(item["toolTimeoutSec"]) if item.get("toolTimeoutSec") is not None else None,
        direct_tools=_parse_direct_tools(item.get("directTools")),
        enabled=bool(item.get("enabled", True)),
    )


def _parse_direct_tools(value: Any) -> bool | tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    raise SyncError("directTools must be a boolean or list of tool names")


def _optional_path(value: Any, repo_root: Path | None = None) -> Path | None:
    if value in (None, ""):
        return None
    return _resolve_path(value, repo_root or Path.cwd())


def _optional_string(value: Any, repo_root: Path) -> str | None:
    if value in (None, ""):
        return None
    return _expand_string_template(str(value), repo_root)


def _resolve_path(value: Any, repo_root: Path) -> Path:
    return Path(_expand_string_template(str(value), repo_root))


def _expand_string_template(value: str, repo_root: Path) -> str:
    expanded = value.replace("${REPO_ROOT}", str(repo_root)).replace("${HOME}", str(Path.home()))
    return os.path.expanduser(expanded)


def _legacy_default_target_paths(target_name: str) -> dict[str, Path | tuple[Path, ...]]:
    home = Path.home()
    if target_name == "codex":
        codex_home = home / ".codex"
        return {
            "config_path": codex_home / "config.toml",
            "skills_dirs": (codex_home / "skills-shared", codex_home / "skills"),
        }
    if target_name == "claude":
        return {
            "config_path": home / ".claude.json",
            "skills_dirs": (home / ".claude" / "skills",),
        }
    if target_name == "opencode":
        return {
            "config_path": home / ".config" / "opencode" / "opencode.jsonc",
            "skills_dirs": (),
        }
    raise ValueError(f"Unknown target name: {target_name}")


def _infer_legacy_config_path(config_path: Path, previous_names: list[str]) -> Path | None:
    if not previous_names or not config_path.exists():
        return None
    return config_path


def _infer_legacy_skills_dir(config_path: Path, previous_names: list[str], candidates: tuple[str, ...]) -> Path | None:
    return _infer_legacy_skills_dir_from_candidates(
        previous_names,
        tuple(config_path.parent / candidate for candidate in candidates),
    )


def _infer_legacy_skills_dir_from_candidates(previous_names: list[str], candidates: tuple[Path, ...]) -> Path | None:
    if not previous_names:
        return None
    for path in candidates:
        if not path.is_dir():
            continue
        if _skill_manifest_path(path).exists():
            return path
        for name in previous_names:
            if (path / name).exists() or (path / name).is_symlink():
                return path
    return None


def _render_source_server(server: McpServerConfig) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": server.transport, "enabled": server.enabled}
    if server.direct_tools is not None:
        payload["directTools"] = list(server.direct_tools) if isinstance(server.direct_tools, tuple) else server.direct_tools
    if server.transport == "stdio":
        payload["command"] = _require_stdio_command(server)
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
        command = _require_stdio_command(server)
        lines.extend(
            [
                f"[mcp_servers.{server.name}]",
                'type = "stdio"',
                f'command = "{_escape(command)}"',
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
            "command": _require_stdio_command(server),
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
            "command": [_require_stdio_command(server), *server.args],
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


def _render_standard_mcp_server(server: McpServerConfig) -> dict[str, Any]:
    if server.transport == "stdio":
        payload: dict[str, Any] = {"command": _require_stdio_command(server)}
        if server.args:
            payload["args"] = list(server.args)
        if server.cwd:
            payload["cwd"] = server.cwd
        if server.env:
            payload["env"] = server.env
    else:
        if not server.url:
            raise SyncError(f"Missing url for remote server '{server.name}'")
        payload = {"url": server.url}
        if server.headers:
            payload["headers"] = server.headers
    if server.tool_timeout_sec is not None:
        payload["toolTimeoutSec"] = server.tool_timeout_sec
    if server.direct_tools is not None:
        payload["directTools"] = list(server.direct_tools) if isinstance(server.direct_tools, tuple) else server.direct_tools
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
    return _load_jsonc_text(path.read_text(encoding="utf-8"))


def _load_jsonc_text(text: str) -> dict[str, Any]:
    if not text.strip():
        return {}
    try:
        return json.loads(_strip_jsonc_comments(text))
    except json.JSONDecodeError as exc:
        raise SyncError(f"Invalid JSONC object entry: {exc.msg}") from exc


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


def _upsert_jsonc_top_level_value(text: str, key: str, value: Any) -> str:
    rendered = _render_jsonc_top_level_entry(key, value)
    span = _find_jsonc_top_level_key_span(text, key)
    if span is not None:
        start, end, has_trailing_comma = span
        replacement = rendered + ("," if has_trailing_comma else "")
        return text[:start] + replacement + text[end:]
    return _insert_jsonc_top_level_entry(text, rendered)


def _render_jsonc_top_level_entry(key: str, value: Any) -> str:
    rendered = json.dumps(value, indent=2, ensure_ascii=False)
    lines = rendered.splitlines()
    if len(lines) == 1:
        return f'  "{key}": {lines[0]}'
    return f'  "{key}": {lines[0]}\n' + "\n".join(f"  {line}" for line in lines[1:])


def _find_jsonc_top_level_key_span(text: str, key: str) -> tuple[int, int, bool] | None:
    root_start, _ = _find_jsonc_root_object_span(text)
    index = root_start + 1
    while True:
        index = _skip_jsonc_trivia(text, index)
        if index >= len(text) or text[index] == "}":
            return None
        entry_start = index
        if text[index] != '"':
            raise SyncError("OpenCode config must use quoted top-level keys")
        key_end, parsed_key = _consume_json_string(text, index)
        index = _skip_jsonc_trivia(text, key_end)
        if index >= len(text) or text[index] != ":":
            raise SyncError("Invalid JSONC object entry")
        value_start = _skip_jsonc_trivia(text, index + 1)
        value_end = _consume_jsonc_value(text, value_start)
        index = _skip_jsonc_trivia(text, value_end)
        has_trailing_comma = index < len(text) and text[index] == ","
        entry_end = index + 1 if has_trailing_comma else index
        if parsed_key == key:
            return entry_start, entry_end, has_trailing_comma
        index = entry_end


def _insert_jsonc_top_level_entry(text: str, entry: str) -> str:
    _, root_end = _find_jsonc_root_object_span(text)
    closing_brace_index = root_end - 1
    if not _jsonc_top_level_has_entries(text):
        return text[:closing_brace_index] + f"{entry}\n" + text[closing_brace_index:]
    last_entry_end = _find_last_jsonc_top_level_entry_end(text)
    return text[:last_entry_end] + f",\n{entry}" + text[last_entry_end:]


def _jsonc_top_level_has_entries(text: str) -> bool:
    root_start, _ = _find_jsonc_root_object_span(text)
    index = _skip_jsonc_trivia(text, root_start + 1)
    return index < len(text) and text[index] != "}"


def _find_last_jsonc_top_level_entry_end(text: str) -> int:
    root_start, _ = _find_jsonc_root_object_span(text)
    index = root_start + 1
    last_entry_end: int | None = None
    while True:
        index = _skip_jsonc_trivia(text, index)
        if index >= len(text) or text[index] == "}":
            break
        if text[index] != '"':
            raise SyncError("OpenCode config must use quoted top-level keys")
        key_end, _ = _consume_json_string(text, index)
        index = _skip_jsonc_trivia(text, key_end)
        if index >= len(text) or text[index] != ":":
            raise SyncError("Invalid JSONC object entry")
        value_start = _skip_jsonc_trivia(text, index + 1)
        value_end = _consume_jsonc_value(text, value_start)
        last_entry_end = value_end
        index = _skip_jsonc_trivia(text, value_end)
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        break
    if last_entry_end is None:
        raise SyncError("OpenCode config has no top-level entries to append after")
    return last_entry_end


def _find_jsonc_root_object_span(text: str) -> tuple[int, int]:
    root_start = _skip_jsonc_trivia(text, 0)
    if root_start >= len(text) or text[root_start] != "{":
        raise SyncError("OpenCode config must be a JSON object")
    return root_start, _consume_jsonc_object(text, root_start)


def _consume_jsonc_object(text: str, index: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    string_char = ""
    in_line_comment = False
    in_block_comment = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
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
        if char == "{":
            depth += 1
            index += 1
            continue
        if char == "}":
            depth -= 1
            index += 1
            if depth == 0:
                return index
            continue
        index += 1
    raise SyncError("OpenCode config must be a JSON object")


def _skip_jsonc_trivia(text: str, index: int) -> int:
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if char.isspace():
            index += 1
            continue
        if char == "/" and next_char == "/":
            index += 2
            while index < len(text) and text[index] != "\n":
                index += 1
            continue
        if char == "/" and next_char == "*":
            index += 2
            while index + 1 < len(text) and not (text[index] == "*" and text[index + 1] == "/"):
                index += 1
            index += 2
            continue
        break
    return index


def _consume_json_string(text: str, index: int) -> tuple[int, str]:
    end = index + 1
    escaped = False
    while end < len(text):
        char = text[end]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            end += 1
            return end, json.loads(text[index:end])
        end += 1
    raise SyncError("Unterminated JSON string")


def _consume_jsonc_value(text: str, index: int) -> int:
    depth = 0
    in_string = False
    escaped = False
    string_char = ""
    in_line_comment = False
    in_block_comment = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if in_line_comment:
            if char == "\n":
                in_line_comment = False
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
        if char in "{[":
            depth += 1
            index += 1
            continue
        if char in "}]":
            if depth == 0:
                return index
            depth -= 1
            index += 1
            continue
        if depth == 0 and char == ",":
            return index
        index += 1
    return index


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


def _systemd_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _require_stdio_command(server: McpServerConfig) -> str:
    if not server.command:
        raise SyncError(f"Missing command for stdio server '{server.name}'")
    return server.command


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_string_list(data: Any) -> list[str]:
    if not isinstance(data, list):
        return []
    return [str(item) for item in data]


def _parse_string_list_mapping(data: Any) -> dict[str, list[str]]:
    if not isinstance(data, dict):
        return {}
    parsed: dict[str, list[str]] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, (list, tuple)):
            parsed[key] = [str(item) for item in value]
    return parsed


def _skill_manifest_path(target_dir: Path) -> Path:
    return target_dir / SKILL_MANIFEST_NAME


def _load_skill_manifest(target_dir: Path) -> list[str]:
    path = _skill_manifest_path(target_dir)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SyncError(f"Invalid skill manifest: {path}")
    return [str(item) for item in data]


def _write_skill_manifest(target_dir: Path, names: list[str]) -> None:
    _atomic_write_text(
        _skill_manifest_path(target_dir),
        json.dumps(sorted(set(names)), indent=2, ensure_ascii=False) + "\n",
    )


def _atomic_write_text(path: Path, content: str) -> None:
    write_target = _output_write_target(path)
    write_target.parent.mkdir(parents=True, exist_ok=True)
    temp_path = write_target.with_name(f".{write_target.name}.{time.time_ns()}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(write_target)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _output_write_target(path: Path) -> Path:
    return path.resolve() if path.is_symlink() else path


def _run_systemctl(*args: str, check: bool = True) -> dict[str, Any]:
    proc = subprocess.run(("systemctl", *args), capture_output=True, text=True, encoding="utf-8", check=False)
    if check and proc.returncode != 0:
        raise SyncError(proc.stderr.strip() or proc.stdout.strip() or f"systemctl failed: {' '.join(args)}")
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
