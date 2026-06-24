from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ui-ux-pro-max-search")
    parser.add_argument("query")
    parser.add_argument("--design-system", action="store_true")
    parser.add_argument("--domain", choices=("product", "style", "color", "typography", "ux", "chart"))
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--page")
    parser.add_argument("--stack")
    parser.add_argument("-p", "--project")
    parser.add_argument("-n", "--max-results", type=int, default=8)
    parser.add_argument("-f", "--format", choices=("markdown", "json"), default="markdown")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    skill_text = SKILL_MD.read_text(encoding="utf-8")
    matches = find_relevant_lines(skill_text, args.query, max_results=max(1, args.max_results))
    payload = build_payload(args, matches)

    if args.persist:
        persist_design_system(payload, project_name=args.project or "Project", page_name=args.page)

    if args.format == "json":
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    print(render_markdown(payload))


def find_relevant_lines(skill_text: str, query: str, *, max_results: int) -> list[str]:
    tokens = re.findall(r"[a-z0-9-]+", query.lower())
    matches: list[str] = []
    for raw_line in skill_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("```"):
            continue
        lowered = line.lower()
        if tokens and not any(token in lowered for token in tokens):
            continue
        matches.append(line)
        if len(matches) >= max_results:
            break
    if matches:
        return matches

    fallback: list[str] = []
    for raw_line in skill_text.splitlines():
        line = raw_line.strip()
        if line.startswith("- `") or line.startswith("| ") or line.startswith("### "):
            fallback.append(line)
        if len(fallback) >= max_results:
            break
    return fallback


def build_payload(args: argparse.Namespace, matches: list[str]) -> dict[str, object]:
    focus = "design-system" if args.design_system else args.domain or "general"
    summary = [f"Query: {args.query}", f"Focus: {focus}"]
    if args.project:
        summary.append(f"Project: {args.project}")
    if args.page:
        summary.append(f"Page: {args.page}")
    if args.stack:
        summary.append(f"Stack: {args.stack}")
    return {
        "query": args.query,
        "focus": focus,
        "project": args.project,
        "page": args.page,
        "stack": args.stack,
        "summary": summary,
        "matches": matches,
        "skill_path": str(SKILL_MD),
    }


def persist_design_system(payload: dict[str, object], *, project_name: str, page_name: str | None) -> None:
    output_root = Path.cwd() / "design-system"
    output_root.mkdir(parents=True, exist_ok=True)
    master_path = output_root / "MASTER.md"
    master_path.write_text(render_markdown(payload), encoding="utf-8")
    if page_name:
        pages_dir = output_root / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        page_path = pages_dir / f"{page_name}.md"
        page_path.write_text(
            "\n".join(
                [
                    f"# {project_name} / {page_name}",
                    "",
                    "This page-specific file overrides the shared MASTER.md guidance when needed.",
                    "",
                    render_markdown(payload),
                ]
            )
            + "\n",
            encoding="utf-8",
        )


def render_markdown(payload: dict[str, object]) -> str:
    lines = ["# UI/UX Pro Max Search", ""]
    lines.extend(f"- {item}" for item in payload["summary"])
    lines.extend(["", "## Matches", ""])
    matches = payload["matches"]
    if isinstance(matches, list) and matches:
        lines.extend(f"- {item}" for item in matches)
    else:
        lines.append("- No direct match found in the vendored skill guidance.")
    lines.extend(["", "## Source", "", f"- {payload['skill_path']}", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
