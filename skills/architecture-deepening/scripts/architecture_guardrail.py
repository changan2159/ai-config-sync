#!/usr/bin/env python3
"""Lightweight deterministic guardrail for architecture-deepening.

Checks the current git diff for a few high-signal structural risks:
- existing large files that are still growing
- suspicious generic file names such as helper/util/manager/common
- newly added files with generic names
- likely pass-through methods in C# diffs
- large changed files that mix multiple responsibility keywords in the added lines

This script is intentionally heuristic. It does not block work; it prints warnings that
should trigger a deeper owner/seam review.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


GENERIC_TOKENS = (
    "helper",
    "helpers",
    "util",
    "utils",
    "manager",
    "common",
    "misc",
    "basehelper",
)

RESPONSIBILITY_PATTERNS = {
    "controller-http": (
        "controller",
        "httppost",
        "httpget",
        "httpput",
        "httpdelete",
        "executeasync",
        "executebooleanasync",
        "executeboolasync",
    ),
    "validation": ("validate", "validator", "validation"),
    "mapping": ("mapper", "adapt", "mapster", "mapto", "todata", "todto"),
    "permission-auth": ("permission", "permissions", "authorize", "auth", "role"),
}


@dataclass
class WarningItem:
    code: str
    path: Path
    detail: str


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def changed_files(repo: Path) -> list[tuple[str, Path]]:
    output = run_git(repo, "diff", "--numstat", "--find-renames", "HEAD")
    items: list[tuple[str, Path]] = []
    for raw_line in output.splitlines():
        parts = raw_line.split("\t")
        if len(parts) < 3:
            continue
        status_path = parts[2]
        if " => " in status_path:
            status_path = status_path.split(" => ", 1)[1]
        items.append((parts[0], repo / status_path))
    for rel_path in untracked_files(repo):
        items.append(("0", repo / rel_path))
    return items


def untracked_files(repo: Path) -> list[Path]:
    output = run_git(repo, "status", "--porcelain")
    paths: list[Path] = []
    for raw_line in output.splitlines():
        if not raw_line.startswith("?? "):
            continue
        paths.append(Path(raw_line[3:]))
    return paths


def diff_patch(repo: Path, rel_path: Path) -> str:
    if not path_exists_in_head(repo, rel_path):
        try:
            return (repo / rel_path).read_text(encoding="utf-8")
        except (FileNotFoundError, UnicodeDecodeError, OSError):
            return ""
    return run_git(repo, "diff", "--find-renames", "HEAD", "--", rel_path.as_posix())


def staged_or_worktree(repo: Path) -> bool:
    status = run_git(repo, "status", "--porcelain")
    return bool(status.strip())


def file_line_count(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("r", encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        return -1


def generic_name(path: Path) -> bool:
    stem = path.stem.lower()
    return any(token in stem for token in GENERIC_TOKENS)


def added_lines_from_patch(patch_text: str) -> list[str]:
    lines: list[str] = []
    if not patch_text:
        return lines
    if not patch_text.startswith("diff --git "):
        return patch_text.splitlines()
    for raw in patch_text.splitlines():
        if raw.startswith("+++") or raw.startswith("@@"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
    return lines


def detect_pass_through_method(added_lines: list[str]) -> bool:
    joined = "\n".join(added_lines)
    if "=>" in joined and ("return " in joined or "Task<" in joined or "async " in joined):
        return True

    signature_indexes: list[int] = []
    for index, line in enumerate(added_lines):
        stripped = line.strip()
        if "(" in stripped and ")" in stripped and "{" in stripped:
            signature_indexes.append(index)

    for start in signature_indexes:
        window = added_lines[start : start + 6]
        body = "\n".join(window)
        if re.search(r"return\s+[A-Za-z_][A-Za-z0-9_\.]*\s*\([^;]*\);", body):
            non_empty = [line.strip() for line in window if line.strip() and line.strip() not in {"{", "}"}]
            if len(non_empty) <= 4:
                return True
    return False


def responsibility_mix(added_lines: list[str]) -> set[str]:
    text = "\n".join(added_lines).lower()
    hits: set[str] = set()
    for label, patterns in RESPONSIBILITY_PATTERNS.items():
        if any(token in text for token in patterns):
            hits.add(label)
    return hits


def collect_warnings(repo: Path, large_file_threshold: int, growth_threshold: int) -> list[WarningItem]:
    warnings: list[WarningItem] = []
    for added_text, abs_path in changed_files(repo):
        rel_path = abs_path.relative_to(repo)
        added_lines = 0 if added_text == "-" else int(added_text)
        current_lines = file_line_count(abs_path)
        is_new_file = not path_exists_in_head(repo, rel_path)
        patch_text = diff_patch(repo, rel_path)
        added_lines_only = added_lines_from_patch(patch_text)

        if current_lines >= large_file_threshold and added_lines >= growth_threshold:
            warnings.append(
                WarningItem(
                    code="large-file-growth",
                    path=rel_path,
                    detail=(
                        f"file has {current_lines} lines and this diff adds {added_lines} lines; "
                        "recheck owner/seam before extending it further"
                    ),
                )
            )

        mixed = responsibility_mix(added_lines_only)
        if current_lines >= large_file_threshold and len(mixed) >= 2:
            warnings.append(
                WarningItem(
                    code="mixed-responsibility-growth",
                    path=rel_path,
                    detail=(
                        "large changed file adds lines matching multiple responsibility buckets "
                        f"({', '.join(sorted(mixed))}); recheck whether logic should be split behind a clearer owner"
                    ),
                )
            )

        if generic_name(rel_path):
            label = "new generic file name" if is_new_file else "generic file name in changed file"
            warnings.append(
                WarningItem(
                    code="generic-name",
                    path=rel_path,
                    detail=(
                        f"{label}; recheck whether the abstraction should have a domain-shaped name "
                        "or a different owner"
                    ),
                )
            )

        if rel_path.suffix.lower() == ".cs" and detect_pass_through_method(added_lines_only):
            warnings.append(
                WarningItem(
                    code="pass-through-method",
                    path=rel_path,
                    detail=(
                        "diff appears to add a likely pass-through method; confirm it removes real caller knowledge "
                        "instead of only renaming or forwarding an existing call"
                    ),
                )
            )

    return warnings


def path_exists_in_head(repo: Path, rel_path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"HEAD:{rel_path.as_posix()}"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode == 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", nargs="?", default=".", help="Path to a git repository")
    parser.add_argument(
        "--large-file-threshold",
        type=int,
        default=300,
        help="Warn when an existing file at or above this line count is still growing",
    )
    parser.add_argument(
        "--growth-threshold",
        type=int,
        default=25,
        help="Warn when the diff adds at least this many lines to a large file",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()

    if not (repo / ".git").exists():
        print(f"error: {repo} is not a git repository", file=sys.stderr)
        return 2

    try:
        if not staged_or_worktree(repo):
            print("No working tree changes detected.")
            return 0
        warnings = collect_warnings(repo, args.large_file_threshold, args.growth_threshold)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not warnings:
        print("No architecture guardrail warnings.")
        return 0

    print("Architecture guardrail warnings:")
    for item in warnings:
        print(f"- [{item.code}] {item.path}: {item.detail}")

    print(
        "\nRecommended follow-up: run a short owner/seam check and decide whether the change "
        "should deepen an existing owner, extract a domain-shaped seam, or leave an explicit debt note."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
