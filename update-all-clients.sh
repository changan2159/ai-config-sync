#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./update-all-clients.sh [--with-pi-web]

Update the main managed client runtimes in sequence:
- Paseo
- Codex
- Claude
- OpenCode
- Pi

Use --with-pi-web to also update the managed pi-web service runtime.
EOF
}

WITH_PI_WEB=false
case "${1:-}" in
  "") ;;
  --with-pi-web) WITH_PI_WEB=true ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown argument: $1" >&2
    usage >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_step() {
  local label="$1"
  shift
  echo
  echo "==> ${label}"
  "$@"
}

run_step "Update Paseo" "${SCRIPT_DIR}/scripts/paseo/update-paseo.sh"
run_step "Update Codex" "${SCRIPT_DIR}/scripts/codex/update-codex.sh"
run_step "Update Claude" "${SCRIPT_DIR}/scripts/claude/update-claude.sh"
run_step "Update OpenCode" "${SCRIPT_DIR}/scripts/opencode/update-opencode.sh"
run_step "Update Pi" "${SCRIPT_DIR}/scripts/pi/update-pi.sh"

if [[ "${WITH_PI_WEB}" == true ]]; then
  run_step "Update pi-web" "${SCRIPT_DIR}/scripts/pi-web/update-pi-web.sh"
fi

echo
printf 'All requested client runtime updates finished.\n'
