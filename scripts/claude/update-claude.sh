#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  claude install "$1" --force
else
  claude update
fi

claude --version
"${script_dir}/ensure-vscode-wrapper.sh"
