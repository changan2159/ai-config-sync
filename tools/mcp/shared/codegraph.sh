#!/bin/bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
if [[ "$SCRIPT_PATH" != */* ]]; then
  SCRIPT_PATH="./$SCRIPT_PATH"
fi
SCRIPT_DIR="$(cd "${SCRIPT_PATH%/*}" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
source "$SCRIPT_DIR/common.sh"
VENDOR_DIR="$REPO_ROOT/vendor/mcp/codegraph"
PACKAGE_DIR="$VENDOR_DIR/node_modules/@colbymchenry/codegraph-linux-x64"
EMBEDDED_NODE="$PACKAGE_DIR/node"
CODEGRAPH_JS="$PACKAGE_DIR/lib/dist/bin/codegraph.js"
BIN_PATH="$VENDOR_DIR/node_modules/.bin/codegraph"
STAMP_FILE="$VENDOR_DIR/.package-lock.sha256"
BOOTSTRAP_VERSION="3"

if [[ ! -f "$VENDOR_DIR/package.json" ]]; then
  echo "ai-config-sync: missing repo-local codegraph source under $VENDOR_DIR" >&2
  exit 1
fi

ai_config_sync_load_runtime_env "$REPO_ROOT"
CURRENT_HASH="$(ai_config_sync_hash_file "$VENDOR_DIR/package-lock.json" "bootstrap-version=$BOOTSTRAP_VERSION;node=$AI_CONFIG_SYNC_TOOLCHAIN_NODE")"

if [[ ! -f "$STAMP_FILE" ]] || [[ ! -x "$BIN_PATH" ]] || [[ ! -x "$EMBEDDED_NODE" ]] || [[ ! -f "$CODEGRAPH_JS" ]] || [[ "$(<"$STAMP_FILE")" != "$CURRENT_HASH" ]]; then
  ai_config_sync_preflight_hint "$REPO_ROOT"
  exit 1
fi

export CODEGRAPH_NO_WATCH=1
export CODEGRAPH_TELEMETRY=0

exec "$EMBEDDED_NODE" --liftoff-only "$CODEGRAPH_JS" "$@"
