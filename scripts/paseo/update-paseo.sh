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
  --fetch-retries 3
  --fetch-retry-mintimeout 2000
  --fetch-retry-maxtimeout 20000
)

expected_launcher="${install_prefix}/bin/paseo"
package_launcher="${install_prefix}/lib/node_modules/@getpaseo/cli/bin/paseo"

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

echo "Updating Paseo via: ${install_cmd[*]}"
attempt=1
max_attempts=3
while true; do
  if "${install_cmd[@]}"; then
    break
  fi
  exit_code=$?
  repair_launcher || true
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

restart_cmd=(paseo restart --home "${PASEO_HOME}")
if status_json="$(paseo status --json 2>/dev/null)"; then
  mapfile -t restart_args < <(
    python3 - <<'PY' <<<"${status_json}"
import json
import sys

try:
    payload = json.load(sys.stdin)
except json.JSONDecodeError:
    raise SystemExit(0)

listen = payload.get("listen")
relay = payload.get("relay")
if isinstance(listen, str) and listen.strip():
    print("--listen")
    print(listen.strip())
if relay in (None, "", "disabled", False):
    print("--no-relay")
elif isinstance(relay, str) and relay.startswith("wss://"):
    print("--relay-use-tls")
PY
  )
  if [[ ${#restart_args[@]} -gt 0 ]]; then
    restart_cmd+=("${restart_args[@]}")
  fi
fi

"${restart_cmd[@]}"
paseo --version
paseo status --json
