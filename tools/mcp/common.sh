#!/bin/bash
set -euo pipefail

ai_config_sync_preflight_hint() {
  local repo_root="$1"
  echo "ai-config-sync: repo-local MCP runtime is missing or stale; run $repo_root/.venv/bin/python -m ai_config_sync.cli mcp-preflight" >&2
}

ai_config_sync_load_runtime_env() {
  local repo_root="$1"
  local env_file="$repo_root/vendor/toolchain/runtime-env.sh"

  if [[ ! -f "$env_file" ]]; then
    ai_config_sync_preflight_hint "$repo_root"
    exit 1
  fi

  # shellcheck disable=SC1090
  source "$env_file"

  local required_vars=(
    AI_CONFIG_SYNC_TOOLCHAIN_PYTHON
    AI_CONFIG_SYNC_TOOLCHAIN_UV
    AI_CONFIG_SYNC_TOOLCHAIN_NODE
    AI_CONFIG_SYNC_TOOLCHAIN_NPM
  )
  local var_name
  for var_name in "${required_vars[@]}"; do
    if [[ -z "${!var_name:-}" ]] || [[ ! -x "${!var_name}" ]]; then
      ai_config_sync_preflight_hint "$repo_root"
      exit 1
    fi
  done
}

ai_config_sync_hash_file() {
  local python_bin="$AI_CONFIG_SYNC_TOOLCHAIN_PYTHON"
  local file_path="$1"
  local salt="${2:-}"

  "$python_bin" - <<'PY' "$file_path" "$salt"
from __future__ import annotations

import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
salt = sys.argv[2]
digest = hashlib.sha256()
digest.update(path.read_bytes())
if salt:
    digest.update(salt.encode("utf-8"))
print(digest.hexdigest())
PY
}

ai_config_sync_hash_serena_manager_source() {
  local python_bin="$AI_CONFIG_SYNC_TOOLCHAIN_PYTHON"
  local vendor_dir="$1"
  local salt="${2:-}"

  "$python_bin" - <<'PY' "$vendor_dir" "$salt"
from __future__ import annotations

import hashlib
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
salt = sys.argv[2]
digest = hashlib.sha256()
for relative in ["pyproject.toml", "uv.lock"]:
    path = root / relative
    digest.update(relative.encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
for path in sorted((root / "src" / "serena_manager").rglob("*.py")):
    digest.update(str(path.relative_to(root)).encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
if salt:
    digest.update(salt.encode("utf-8"))
print(digest.hexdigest())
PY
}
