#!/usr/bin/env python3
"""Audit local Codex skill directories for drift and metadata issues."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_SWITCH_ROOT = Path(r"C:\Users\admin\.cc-switch\skills")
DEFAULT_CODEX_ROOT = Path(r"C:\Users\admin\.codex\skills")
ALLOWED_FRONTMATTER_KEYS = {"name", "description"}


@dataclass
class SkillIssue:
    severity: str
    category: str
    skill: str
    path: Path
    detail: str


def discover_skills(root: Path, *, include_hidden: bool = False) -> dict[str, Path]:
    skills: dict[str, Path] = {}
    if not root.exists():
        return skills
    for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue
        if not include_hidden and child.name.startswith("."):
            continue
        if (child / "SKILL.md").exists():
            skills[child.name] = child
    return skills


def read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def is_expected_codex_mirror(skill: str, codex_path: Path, switch_root: Path) -> bool:
    if not codex_path.is_symlink():
        return False

    try:
        return codex_path.resolve() == (switch_root / skill).resolve()
    except OSError:
        return False


def parse_frontmatter_keys(skill_md: Path) -> list[str]:
    text = read_text_utf8(skill_md)
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        raise ValueError("SKILL.md is missing YAML frontmatter")

    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        raise ValueError("SKILL.md frontmatter is not closed")

    keys: list[str] = []
    for line in lines[1:end_index]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith((" ", "\t")):
            continue
        if ":" in line:
            keys.append(line.split(":", 1)[0].strip())
    return keys


def load_yaml(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def validate_openai_yaml(skill: str, skill_dir: Path, yaml_path: Path) -> list[SkillIssue]:
    issues: list[SkillIssue] = []

    try:
        data = load_yaml(yaml_path)
    except yaml.YAMLError as exc:
        return [
            SkillIssue(
                severity="error",
                category="yaml",
                skill=skill,
                path=yaml_path,
                detail=f"Invalid YAML in agents/openai.yaml: {exc}",
            )
        ]

    if not isinstance(data, dict):
        return [
            SkillIssue(
                severity="error",
                category="yaml",
                skill=skill,
                path=yaml_path,
                detail="agents/openai.yaml must parse to a mapping.",
            )
        ]

    interface = data.get("interface")
    if not isinstance(interface, dict):
        return [
            SkillIssue(
                severity="error",
                category="metadata",
                skill=skill,
                path=yaml_path,
                detail="agents/openai.yaml is missing interface metadata.",
            )
        ]

    for key in ("display_name", "short_description", "default_prompt"):
        value = interface.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                SkillIssue(
                    severity="warning",
                    category="metadata",
                    skill=skill,
                    path=yaml_path,
                    detail=f"interface.{key} is missing or empty.",
                )
            )

    short_description = interface.get("short_description")
    if isinstance(short_description, str):
        length = len(short_description.strip())
        if length < 25 or length > 64:
            issues.append(
                SkillIssue(
                    severity="warning",
                    category="metadata",
                    skill=skill,
                    path=yaml_path,
                    detail=(
                        "interface.short_description should be 25-64 characters for UI "
                        f"scanning; current length is {length}."
                    ),
                )
            )

    default_prompt = interface.get("default_prompt")
    expected_skill_ref = f"${skill}"
    if isinstance(default_prompt, str) and expected_skill_ref not in default_prompt:
        issues.append(
            SkillIssue(
                severity="warning",
                category="metadata",
                skill=skill,
                path=yaml_path,
                detail=(
                    "interface.default_prompt should explicitly mention the skill as "
                    f"{expected_skill_ref}."
                ),
            )
        )

    policy = data.get("policy")
    if not isinstance(policy, dict) or "allow_implicit_invocation" not in policy:
        issues.append(
            SkillIssue(
                severity="warning",
                category="metadata",
                skill=skill,
                path=yaml_path,
                detail="policy.allow_implicit_invocation is missing.",
            )
        )

    for icon_key in ("icon_small", "icon_large"):
        icon_value = interface.get(icon_key)
        if isinstance(icon_value, str):
            icon_path = skill_dir / icon_value.replace("./", "", 1)
            if not icon_path.exists():
                issues.append(
                    SkillIssue(
                        severity="warning",
                        category="metadata",
                        skill=skill,
                        path=yaml_path,
                        detail=f"{icon_key} points to a missing file: {icon_value}.",
                    )
                )

    return issues


def collect_issues(
    switch_root: Path,
    codex_root: Path,
    *,
    require_agents_yaml: bool,
) -> list[SkillIssue]:
    issues: list[SkillIssue] = []

    switch_skills = discover_skills(switch_root)
    codex_system_skills = discover_skills(codex_root, include_hidden=True)
    codex_user_skills = {
        name: path
        for name, path in codex_system_skills.items()
        if name != ".system"
    }

    for name, path in sorted(codex_user_skills.items()):
        if is_expected_codex_mirror(name, path, switch_root):
            continue

        detail = (
            "User-managed skill exists under .codex/skills; keep user skills under "
            ".cc-switch/skills instead."
        )
        category = "source_of_truth"
        if path.is_symlink():
            detail = (
                "Skill under .codex/skills is a symbolic link, but it does not point to "
                "the matching .cc-switch source-of-truth skill."
            )
            category = "unexpected_link_target"

        issues.append(
            SkillIssue(
                severity="error",
                category=category,
                skill=name,
                path=path,
                detail=detail,
            )
        )

    duplicate_names = sorted(set(switch_skills) & set(codex_user_skills))
    for name in duplicate_names:
        if is_expected_codex_mirror(name, codex_user_skills[name], switch_root):
            continue
        issues.append(
            SkillIssue(
                severity="error",
                category="duplicate_skill",
                skill=name,
                path=switch_skills[name],
                detail="Skill exists in both .cc-switch and .codex user-skill roots.",
            )
        )

    missing_codex_mirrors = sorted(set(switch_skills) - set(codex_user_skills))
    for name in missing_codex_mirrors:
        issues.append(
            SkillIssue(
                severity="warning",
                category="missing_codex_mirror",
                skill=name,
                path=switch_skills[name],
                detail=(
                    "Skill exists under .cc-switch/skills but has no matching "
                    ".codex/skills symbolic-link mirror; Codex discovery may be incomplete."
                ),
            )
        )

    for root_label, skills in (("cc-switch", switch_skills), ("codex", codex_user_skills)):
        for name, skill_dir in sorted(skills.items()):
            skill_md = skill_dir / "SKILL.md"
            try:
                keys = parse_frontmatter_keys(skill_md)
            except UnicodeDecodeError:
                issues.append(
                    SkillIssue(
                        severity="error",
                        category="encoding",
                        skill=name,
                        path=skill_md,
                        detail="SKILL.md is not valid UTF-8.",
                    )
                )
                continue
            except ValueError as exc:
                issues.append(
                    SkillIssue(
                        severity="error",
                        category="frontmatter",
                        skill=name,
                        path=skill_md,
                        detail=str(exc),
                    )
                )
                continue

            extra_keys = [key for key in keys if key not in ALLOWED_FRONTMATTER_KEYS]
            if extra_keys:
                issues.append(
                    SkillIssue(
                        severity="warning",
                        category="frontmatter",
                        skill=name,
                        path=skill_md,
                        detail=f"Non-standard frontmatter keys present: {', '.join(extra_keys)}.",
                    )
                )

            if require_agents_yaml and root_label == "cc-switch":
                agents_yaml = skill_dir / "agents" / "openai.yaml"
                if not agents_yaml.exists():
                    issues.append(
                        SkillIssue(
                            severity="warning",
                            category="metadata",
                            skill=name,
                            path=skill_dir,
                            detail="Missing agents/openai.yaml metadata file.",
                        )
                    )
                else:
                    issues.extend(validate_openai_yaml(name, skill_dir, agents_yaml))

    return issues


def print_report(
    *,
    switch_root: Path,
    codex_root: Path,
    issues: list[SkillIssue],
) -> None:
    switch_skills = discover_skills(switch_root)
    codex_all = discover_skills(codex_root, include_hidden=True)
    codex_user_skills = {name: path for name, path in codex_all.items() if name != ".system"}

    print("Skill audit report")
    print(f"- cc-switch root: {switch_root}")
    print(f"- codex root: {codex_root}")
    print(f"- cc-switch skills: {len(switch_skills)}")
    print(f"- codex user skills: {len(codex_user_skills)}")
    print(f"- issue count: {len(issues)}")

    if not issues:
        print("\nPASS: no drift or metadata issues detected.")
        return

    grouped: dict[str, list[SkillIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.severity, []).append(issue)

    for severity in ("error", "warning"):
        bucket = grouped.get(severity, [])
        if not bucket:
            continue
        print(f"\n{severity.upper()}S")
        for issue in bucket:
            print(
                f"- [{issue.category}] {issue.skill}: {issue.detail} "
                f"({issue.path})"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit local skill directories.")
    parser.add_argument(
        "--switch-root",
        default=str(DEFAULT_SWITCH_ROOT),
        help="Root directory for user-managed skills.",
    )
    parser.add_argument(
        "--codex-root",
        default=str(DEFAULT_CODEX_ROOT),
        help="Root directory for Codex-managed skills.",
    )
    parser.add_argument(
        "--allow-missing-agents",
        action="store_true",
        help="Do not warn when a .cc-switch skill lacks agents/openai.yaml.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings as well as errors.",
    )
    args = parser.parse_args()

    switch_root = Path(args.switch_root).expanduser().resolve()
    codex_root = Path(args.codex_root).expanduser().resolve()

    issues = collect_issues(
        switch_root,
        codex_root,
        require_agents_yaml=not args.allow_missing_agents,
    )
    print_report(switch_root=switch_root, codex_root=codex_root, issues=issues)

    has_errors = any(issue.severity == "error" for issue in issues)
    has_warnings = any(issue.severity == "warning" for issue in issues)

    if has_errors:
        return 2
    if args.strict and has_warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
