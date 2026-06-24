#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_playwright_regression.sh --project-dir DIR --command "npm run regression:live-browser" [options]

Options:
  --project-dir DIR           Frontend project directory containing package.json
  --command CMD               Main browser regression command to run
  --smoke-command CMD         Optional smoke command to run before the main command
  --install-command CMD       Optional dependency install command to run when requested
  --skip-browser-install      Skip `npx playwright install chromium`
  --help                      Show this help

Examples:
  run_playwright_regression.sh \
    --project-dir /repo/frontend/console \
    --command "npm run regression:live-browser"

  run_playwright_regression.sh \
    --project-dir /repo/apps/web \
    --smoke-command "npm run smoke:browser" \
    --command "npx playwright test"
EOF
}

project_dir=""
main_command=""
smoke_command=""
install_command=""
skip_browser_install=0
host_platform_override="${PLAYWRIGHT_HOST_PLATFORM_OVERRIDE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir)
      project_dir="${2:-}"
      shift 2
      ;;
    --command)
      main_command="${2:-}"
      shift 2
      ;;
    --smoke-command)
      smoke_command="${2:-}"
      shift 2
      ;;
    --install-command)
      install_command="${2:-}"
      shift 2
      ;;
    --skip-browser-install)
      skip_browser_install=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$project_dir" || -z "$main_command" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -d "$project_dir" ]]; then
  echo "Project directory does not exist: $project_dir" >&2
  exit 2
fi

if [[ ! -f "$project_dir/package.json" ]]; then
  echo "package.json not found under: $project_dir" >&2
  exit 2
fi

cd "$project_dir"

if [[ -z "$host_platform_override" && -f /etc/os-release ]]; then
  . /etc/os-release
  if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" =~ ^([0-9]+)\.([0-9]+)$ ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    if (( major > 24 || (major == 24 && minor > 4) )); then
      host_platform_override="ubuntu24.04-x64"
      echo "[step] host override Playwright platform -> ${host_platform_override}"
    fi
  fi
fi

export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="${host_platform_override}"

if [[ -n "$install_command" ]]; then
  echo "[step] install project dependencies"
  bash -lc "$install_command"
fi

if [[ $skip_browser_install -eq 0 ]]; then
  echo "[step] ensure Playwright bundled Chromium"
  npx playwright install chromium
else
  echo "[step] skip browser install"
fi

if [[ -n "$smoke_command" ]]; then
  echo "[step] run smoke command"
  bash -lc "$smoke_command"
fi

echo "[step] run main regression command"
bash -lc "$main_command"
