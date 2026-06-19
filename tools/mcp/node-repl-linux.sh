#!/bin/bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ "$SCRIPT_PATH" != */* ]]; then
  SCRIPT_PATH="./$SCRIPT_PATH"
fi
SCRIPT_DIR="$(cd "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/common.sh"
VENDOR_DIR="$REPO_ROOT/vendor/mcp/node-repl-linux"
ENTRYPOINT="$VENDOR_DIR/index.mjs"
STAMP_FILE="$VENDOR_DIR/.package-lock.sha256"
BOOTSTRAP_VERSION="3"

if [[ ! -f "$VENDOR_DIR/package.json" || ! -f "$ENTRYPOINT" ]]; then
  echo "ai-config-sync: missing repo-local node-repl-linux source under $VENDOR_DIR" >&2
  exit 1
fi

ai_config_sync_load_runtime_env "$REPO_ROOT"
CURRENT_HASH="$(ai_config_sync_hash_file "$VENDOR_DIR/package-lock.json" "bootstrap-version=$BOOTSTRAP_VERSION;node=$AI_CONFIG_SYNC_TOOLCHAIN_NODE")"

if [[ ! -f "$STAMP_FILE" ]] || [[ ! -d "$VENDOR_DIR/node_modules" ]] || [[ "$(<"$STAMP_FILE")" != "$CURRENT_HASH" ]]; then
  ai_config_sync_preflight_hint "$REPO_ROOT"
  exit 1
fi

exec "$AI_CONFIG_SYNC_TOOLCHAIN_NODE" "$ENTRYPOINT" "$@"
