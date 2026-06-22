#!/usr/bin/env bash
set -euo pipefail

claude_wrapper="${HOME}/.local/bin/claude"

if [[ ! -x "${claude_wrapper}" ]]; then
  echo "Claude wrapper not found or not executable: ${claude_wrapper}" >&2
  exit 1
fi

update_settings_file() {
  local settings_path="$1"

  mkdir -p "$(dirname "${settings_path}")"

  SETTINGS_PATH="${settings_path}" CLAUDE_WRAPPER="${claude_wrapper}" node <<'NODE'
const fs = require("fs");

const settingsPath = process.env.SETTINGS_PATH;
const claudeWrapper = process.env.CLAUDE_WRAPPER;

function stripJsonComments(text) {
  let result = "";
  let inString = false;
  let escaped = false;
  let lineComment = false;
  let blockComment = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (lineComment) {
      if (char === "\n") {
        lineComment = false;
        result += char;
      }
      continue;
    }

    if (blockComment) {
      if (char === "*" && next === "/") {
        blockComment = false;
        i += 1;
      }
      continue;
    }

    if (inString) {
      result += char;
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === "\"") {
        inString = false;
      }
      continue;
    }

    if (char === "/" && next === "/") {
      lineComment = true;
      i += 1;
      continue;
    }

    if (char === "/" && next === "*") {
      blockComment = true;
      i += 1;
      continue;
    }

    if (char === "\"") {
      inString = true;
    }

    result += char;
  }

  return result;
}

function stripTrailingCommas(text) {
  let result = "";
  let inString = false;
  let escaped = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];

    if (inString) {
      result += char;
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === "\"") {
        inString = false;
      }
      continue;
    }

    if (char === "\"") {
      inString = true;
      result += char;
      continue;
    }

    if (char === ",") {
      let j = i + 1;
      while (j < text.length && /\s/.test(text[j])) {
        j += 1;
      }
      if (text[j] === "}" || text[j] === "]") {
        continue;
      }
    }

    result += char;
  }

  return result;
}

function parseJsonc(text) {
  return JSON.parse(stripTrailingCommas(stripJsonComments(text)));
}

let settings = {};
if (fs.existsSync(settingsPath)) {
  const raw = fs.readFileSync(settingsPath, "utf8").trim();
  if (raw) {
    settings = parseJsonc(raw);
  }
}

if (settings["claudeCode.claudeProcessWrapper"] === claudeWrapper) {
  process.exit(0);
}

settings["claudeCode.claudeProcessWrapper"] = claudeWrapper;
fs.writeFileSync(settingsPath, `${JSON.stringify(settings, null, 2)}\n`, "utf8");
NODE
}

update_settings_file "${HOME}/.config/Code/User/settings.json"

if [[ -d "${HOME}/.vscode-server" ]]; then
  update_settings_file "${HOME}/.vscode-server/data/Machine/settings.json"
fi

echo "VS Code Claude wrapper path set to ${claude_wrapper}"
