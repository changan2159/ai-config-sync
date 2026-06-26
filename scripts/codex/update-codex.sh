#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/codex/update-codex.sh [version]

Update Codex in its current global npm prefix.
If [version] is omitted, installs the latest published version.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

PACKAGE_NAME="@openai/codex"
VERSION="${1:-}"
PACKAGE_SPEC="${PACKAGE_NAME}@${VERSION}"
if [[ -z "${VERSION}" ]]; then
  PACKAGE_SPEC="${PACKAGE_NAME}@latest"
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex launcher not found on PATH" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found on PATH" >&2
  exit 1
fi
npm_bin="$(command -v npm)"

launcher_path="$(command -v codex)"
resolved_launcher="$(readlink -f "${launcher_path}")"

case "${resolved_launcher}" in
  */lib/node_modules/@openai/codex/bin/codex.js)
    install_prefix="${resolved_launcher%/lib/node_modules/@openai/codex/bin/codex.js}"
    ;;
  *)
    install_prefix="${launcher_path%/bin/codex}"
    ;;
esac

if [[ -z "${install_prefix}" || "${install_prefix}" == "${launcher_path}" ]]; then
  echo "Unable to infer Codex install prefix from ${launcher_path}" >&2
  exit 1
fi

install_cmd=("${npm_bin}" install -g --prefix "${install_prefix}" "${PACKAGE_SPEC}")
if [[ ! -w "${install_prefix}" && "$(id -u)" -ne 0 ]]; then
  install_cmd=(sudo "${install_cmd[@]}")
fi

echo "Updating Codex via: ${install_cmd[*]}"
"${install_cmd[@]}"

codex --version
