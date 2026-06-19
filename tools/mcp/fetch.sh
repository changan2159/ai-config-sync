#!/bin/bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ "$SCRIPT_PATH" != */* ]]; then
  SCRIPT_PATH="./$SCRIPT_PATH"
fi
SCRIPT_DIR="$(cd "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/common.sh"
VENDOR_DIR="$REPO_ROOT/vendor/mcp/fetch"
FETCH_BIN="$VENDOR_DIR/.venv/bin/mcp-server-fetch"
REQUIREMENTS_FILE="$VENDOR_DIR/requirements.lock"
STAMP_FILE="$VENDOR_DIR/.requirements.sha256"
BOOTSTRAP_VERSION="3"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
  echo "ai-config-sync: missing repo-local fetch runtime under $VENDOR_DIR" >&2
  exit 1
fi

ai_config_sync_load_runtime_env "$REPO_ROOT"
CURRENT_HASH="$(ai_config_sync_hash_file "$REQUIREMENTS_FILE" "bootstrap-version=$BOOTSTRAP_VERSION;python=$AI_CONFIG_SYNC_TOOLCHAIN_PYTHON")"

if [[ ! -f "$STAMP_FILE" ]] || [[ ! -x "$FETCH_BIN" ]] || [[ "$(<"$STAMP_FILE")" != "$CURRENT_HASH" ]]; then
  ai_config_sync_preflight_hint "$REPO_ROOT"
  exit 1
fi

exec "$FETCH_BIN" "$@"
