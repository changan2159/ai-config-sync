#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing virtualenv python at ${PYTHON_BIN}" >&2
  exit 1
fi

VERSION_ARG=()
if [[ $# -ge 1 && -n "${1:-}" ]]; then
  VERSION_ARG=(--version "$1")
fi

cd "${REPO_ROOT}"

"${PYTHON_BIN}" -m ai_config_sync.cli opencode-install "${VERSION_ARG[@]}"

if systemctl is-enabled opencode-web.service >/dev/null 2>&1; then
  sudo systemctl restart opencode-web.service
else
  sudo "${PYTHON_BIN}" -m ai_config_sync.cli opencode-service-start
fi

"${PYTHON_BIN}" -m ai_config_sync.cli opencode-status
