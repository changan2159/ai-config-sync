#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  claude install "$1" --force
else
  claude update
fi

claude --version
