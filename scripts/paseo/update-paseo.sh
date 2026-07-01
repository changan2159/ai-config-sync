#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/paseo/update-paseo.sh [version]

Update Paseo CLI/server in its current global npm prefix, then restart the
local daemon from PASEO_HOME or ~/.paseo. If [version] is omitted, installs
the latest published version.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

PACKAGE_NAME="@getpaseo/cli"
VERSION="${1:-}"
PACKAGE_SPEC="${PACKAGE_NAME}@${VERSION}"
NPM_INSTALL_TIMEOUT_SEC="${NPM_INSTALL_TIMEOUT_SEC:-300}"
PASEO_RESTART_TIMEOUT_SEC="${PASEO_RESTART_TIMEOUT_SEC:-45}"
if [[ -z "${VERSION}" ]]; then
  PACKAGE_SPEC="${PACKAGE_NAME}@latest"
fi

if ! command -v paseo >/dev/null 2>&1; then
  echo "paseo launcher not found on PATH" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found on PATH" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found on PATH" >&2
  exit 1
fi
npm_bin="$(command -v npm)"

launcher_path="$(command -v paseo)"
resolved_launcher="$(readlink -f "${launcher_path}")"

case "${resolved_launcher}" in
  */lib/node_modules/@getpaseo/cli/bin/paseo)
    install_prefix="${resolved_launcher%/lib/node_modules/@getpaseo/cli/bin/paseo}"
    ;;
  *)
    install_prefix="${launcher_path%/bin/paseo}"
    ;;
esac

if [[ -z "${install_prefix}" || "${install_prefix}" == "${launcher_path}" ]]; then
  echo "Unable to infer Paseo install prefix from ${launcher_path}" >&2
  exit 1
fi

install_cmd=("${npm_bin}" install -g --prefix "${install_prefix}" "${PACKAGE_SPEC}")
if [[ ! -w "${install_prefix}" && "$(id -u)" -ne 0 ]]; then
  install_cmd=(sudo "${install_cmd[@]}")
fi
install_cmd+=(
  --no-fund
  --no-audit
  --fetch-retries 3
  --fetch-retry-mintimeout 2000
  --fetch-retry-maxtimeout 30000
  --fetch-timeout 300000
)

expected_launcher="${install_prefix}/bin/paseo"
package_launcher="${install_prefix}/lib/node_modules/@getpaseo/cli/bin/paseo"
package_scope_dir="${install_prefix}/lib/node_modules/@getpaseo"

cleanup_stale_package_dirs() {
  if [[ ! -d "${package_scope_dir}" ]]; then
    return 0
  fi
  find "${package_scope_dir}" -mindepth 1 -maxdepth 1 -name '.cli-*' -exec rm -rf {} +
}

repair_launcher() {
  mkdir -p "${install_prefix}/bin"
  if [[ -f "${package_launcher}" ]]; then
    chmod +x "${package_launcher}" || true
    ln -sfn ../lib/node_modules/@getpaseo/cli/bin/paseo "${expected_launcher}"
    echo "Repaired Paseo launcher: ${expected_launcher}"
    return 0
  fi
  return 1
}

run_with_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    timeout --foreground "$@"
  else
    shift
    "$@"
  fi
}

restart_paseo_daemon() {
  local home="$1"
  shift
  local restart_args=("$@")
  local restart_cmd=(paseo restart --json --force --timeout 15 --home "${home}")
  if [[ ${#restart_args[@]} -gt 0 ]]; then
    restart_cmd+=("${restart_args[@]}")
  fi
  if run_with_timeout "${PASEO_RESTART_TIMEOUT_SEC}s" "${restart_cmd[@]}"; then
    return 0
  fi

  echo "Paseo restart command did not complete cleanly, falling back to stop/start..." >&2
  run_with_timeout "${PASEO_RESTART_TIMEOUT_SEC}s" paseo daemon stop --json --force --timeout 15 --kill-timeout 5 --home "${home}" || true
  local start_cmd=(paseo daemon start --home "${home}")
  if [[ ${#restart_args[@]} -gt 0 ]]; then
    start_cmd+=("${restart_args[@]}")
  fi
  run_with_timeout "${PASEO_RESTART_TIMEOUT_SEC}s" "${start_cmd[@]}"
}

wait_for_paseo_status() {
  local expected_version="$1"
  local deadline=$((SECONDS + PASEO_RESTART_TIMEOUT_SEC))
  while (( SECONDS < deadline )); do
    if status_json="$(paseo status --json 2>/dev/null)"; then
      if STATUS_JSON="${status_json}" python3 - "${expected_version}" <<'PY' >/dev/null 2>&1
import json
import os
import sys

payload = json.loads(os.environ["STATUS_JSON"])
expected = sys.argv[1]
if payload.get("localDaemon") != "running":
    raise SystemExit(1)
cli_version = payload.get("cliVersion")
daemon_version = payload.get("daemonVersion")
if expected and (cli_version != expected or daemon_version != expected):
    raise SystemExit(1)
PY
      then
        echo "${status_json}"
        return 0
      fi
    fi
    sleep 2
  done
  return 1
}

echo "Updating Paseo via: ${install_cmd[*]}"
attempt=1
max_attempts=3
while true; do
  cleanup_stale_package_dirs
  if command -v timeout >/dev/null 2>&1; then
    run_cmd=(timeout --foreground "${NPM_INSTALL_TIMEOUT_SEC}s" "${install_cmd[@]}")
  else
    run_cmd=("${install_cmd[@]}")
  fi
  if "${run_cmd[@]}"; then
    break
  fi
  exit_code=$?
  repair_launcher || true
  cleanup_stale_package_dirs
  if (( attempt >= max_attempts )); then
    echo "Paseo update failed after ${attempt} attempt(s)." >&2
    exit "${exit_code}"
  fi
  echo "Paseo update attempt ${attempt} failed, retrying..." >&2
  sleep $((attempt * 2))
  attempt=$((attempt + 1))
done

repair_launcher || true

PASEO_HOME="${PASEO_HOME:-${HOME}/.paseo}"
if [[ -f "${PASEO_HOME}/config.json" ]]; then
  backup_path="${PASEO_HOME}/config.json.bak-$(date +%F-%H%M%S)"
  cp "${PASEO_HOME}/config.json" "${backup_path}"
  echo "Backed up ${PASEO_HOME}/config.json -> ${backup_path}"
fi

restart_args=()
if status_json="$(paseo status --json 2>/dev/null)"; then
  mapfile -t restart_args < <(
    STATUS_JSON="${status_json}" python3 - <<'PY'
import json
import os
import sys

try:
    payload = json.loads(os.environ["STATUS_JSON"])
except json.JSONDecodeError:
    raise SystemExit(0)

listen = payload.get("listen")
relay = payload.get("relay")
if isinstance(listen, str) and listen.strip():
    print("--listen")
    print(listen.strip())
if relay in (None, "", "disabled", False):
    print("--no-relay")
PY
  )
fi

restart_paseo_daemon "${PASEO_HOME}" "${restart_args[@]}"
paseo --version
if ! wait_for_paseo_status "${VERSION}"; then
  echo "Paseo daemon did not report a healthy post-restart status within ${PASEO_RESTART_TIMEOUT_SEC}s." >&2
  exit 1
fi
