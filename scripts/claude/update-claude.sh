#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_NAME="@anthropic-ai/claude-code"
CLAUDE_UPDATE_TIMEOUT_SEC="${CLAUDE_UPDATE_TIMEOUT_SEC:-300}"
CLAUDE_UPDATE_HEARTBEAT_SEC="${CLAUDE_UPDATE_HEARTBEAT_SEC:-15}"
CLAUDE_INSTALL_PREFIX_DEFAULT="${HOME}/.local"
CLAUDE_INSTALL_MAX_ATTEMPTS="${CLAUDE_INSTALL_MAX_ATTEMPTS:-3}"

usage() {
  cat <<'EOF'
Usage: ./scripts/claude/update-claude.sh [version]

Update Claude via the managed user npm prefix. When [version] is omitted,
installs the latest published version.
EOF
}

run_with_heartbeat() {
  "$@" &
  local command_pid=$!
  (
    while kill -0 "${command_pid}" 2>/dev/null; do
      sleep "${CLAUDE_UPDATE_HEARTBEAT_SEC}"
      kill -0 "${command_pid}" 2>/dev/null || exit 0
      echo "Claude updater still running..."
    done
  ) &
  local heartbeat_pid=$!
  local status=0
  wait "${command_pid}" || status=$?
  kill "${heartbeat_pid}" 2>/dev/null || true
  wait "${heartbeat_pid}" 2>/dev/null || true
  return "${status}"
}

cleanup_stale_package_dirs() {
  local package_scope_dir="$1/lib/node_modules/@anthropic-ai"
  if [[ ! -d "${package_scope_dir}" ]]; then
    return 0
  fi
  find "${package_scope_dir}" -mindepth 1 -maxdepth 1 -name '.claude-code-*' -exec rm -rf {} +
}

cleanup_zero_byte_native_versions() {
  local versions_dir="${HOME}/.local/share/claude/versions"
  if [[ ! -d "${versions_dir}" ]]; then
    return 0
  fi
  find "${versions_dir}" -mindepth 1 -maxdepth 1 -type f -size 0 -delete
}

prepare_launcher_for_npm_install() {
  local launcher_path="${HOME}/.local/bin/claude"
  if [[ ! -L "${launcher_path}" ]]; then
    return 0
  fi
  local resolved_launcher
  resolved_launcher="$(readlink -f "${launcher_path}")"
  case "${resolved_launcher}" in
    */.local/share/claude/versions/*)
      rm -f "${launcher_path}"
      ;;
  esac
}

resolve_install_prefix() {
  local launcher_path resolved_launcher
  if ! launcher_path="$(command -v claude 2>/dev/null)"; then
    echo "${CLAUDE_INSTALL_PREFIX_DEFAULT}"
    return 0
  fi
  resolved_launcher="$(readlink -f "${launcher_path}")"
  case "${resolved_launcher}" in
    */lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe)
      echo "${resolved_launcher%/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe}"
      ;;
    */.local/share/claude/versions/*)
      echo "${CLAUDE_INSTALL_PREFIX_DEFAULT}"
      ;;
    *)
      echo "${launcher_path%/bin/claude}"
      ;;
  esac
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if command -v timeout >/dev/null 2>&1; then
  timeout_prefix=(timeout --foreground "${CLAUDE_UPDATE_TIMEOUT_SEC}s")
else
  timeout_prefix=()
fi

version="${1:-}"
package_spec="${PACKAGE_NAME}@${version}"
if [[ -z "${version}" ]]; then
  package_spec="${PACKAGE_NAME}@latest"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found on PATH" >&2
  exit 1
fi

install_prefix="$(resolve_install_prefix)"
if [[ -z "${install_prefix}" || "${install_prefix}" == "$(command -v claude 2>/dev/null || true)" ]]; then
  echo "Unable to infer Claude install prefix" >&2
  exit 1
fi

install_cmd=(
  "${timeout_prefix[@]}"
  npm
  install
  -g
  --force
  --prefix
  "${install_prefix}"
  "${package_spec}"
  --no-fund
  --no-audit
  --fetch-retries
  5
  --fetch-retry-mintimeout
  2000
  --fetch-retry-maxtimeout
  30000
  --fetch-timeout
  300000
)

echo "Updating Claude via: npm install -g --prefix ${install_prefix} ${package_spec}"
attempt=1
while true; do
  cleanup_stale_package_dirs "${install_prefix}"
  cleanup_zero_byte_native_versions
  prepare_launcher_for_npm_install
  set +e
  run_with_heartbeat "${install_cmd[@]}"
  exit_code=$?
  set -e
  if [[ ${exit_code} -eq 0 ]]; then
    break
  fi

  if (( attempt >= CLAUDE_INSTALL_MAX_ATTEMPTS )); then
    if [[ ${exit_code} -eq 124 ]]; then
      echo "Claude update timed out after ${CLAUDE_UPDATE_TIMEOUT_SEC}s." >&2
    fi
    exit "${exit_code}"
  fi
  echo "Claude update attempt ${attempt} failed, retrying..." >&2
  sleep $((attempt * 2))
  attempt=$((attempt + 1))
done

cleanup_zero_byte_native_versions

version_output="$(claude --version)"
if [[ $# -ge 1 && -n "${version}" ]]; then
  if [[ "${version_output}" != *"${version}"* ]]; then
    echo "Claude version check failed: expected ${version}, got ${version_output}" >&2
    exit 1
  fi
fi
echo "${version_output}"

"${script_dir}/ensure-vscode-wrapper.sh"
