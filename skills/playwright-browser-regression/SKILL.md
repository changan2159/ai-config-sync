---
name: playwright-browser-regression
description: Run browser regression or browser smoke checks for web projects with Playwright using Playwright's bundled Chromium in headless mode. Use when a user asks to run browser regression, E2E smoke, responsive browser checks, or live browser verification on a local machine or a Linux server without a GUI, especially when the project already has Playwright scripts and should reuse them instead of inventing a new harness.
---

# Playwright Browser Regression

## Overview

Use the repository's existing browser scripts first. Default to Playwright's bundled `chromium` via `npx playwright install chromium`, which works well on headless Linux servers and avoids system-browser version drift.

## Workflow

1. Find the existing frontend/browser entry point before doing anything else.
2. Prefer a repo-owned command such as `npm run regression:live-browser`, `npm run smoke:browser`, `npm run test:e2e`, or `npx playwright test`.
3. Ensure the project uses Playwright's bundled browser instead of a system `chromium` unless the user explicitly wants the system browser.
4. Run in headless mode on servers. Do not require a GUI or `xvfb` unless the project has a hard dependency on headed mode.
5. If the repo has no browser harness, say so plainly and then decide whether to add one.

## Standard Path

Use this order by default:

1. Identify the project directory that owns the frontend and browser scripts.
2. Check for an existing Playwright dependency and browser command in `package.json`.
3. Run the helper script in this skill to install bundled Chromium and execute the repo's own regression command.
4. If the run fails because Linux libraries are missing, read `references/linux-headless-notes.md`.
5. Report the exact command, what passed, and what blocked.

## Preferred Commands

Prefer the repo's native command instead of writing an ad hoc Playwright file:

- Full regression:
  - `npm run regression:live-browser`
  - `npm run test:e2e`
  - `npx playwright test`
- Lighter smoke:
  - `npm run smoke:browser`
  - `npm run test:e2e -- --grep smoke`

If several exist, start with the least destructive smoke/regression script that already matches the repo's conventions.

## Helper Script

Use `scripts/run_playwright_regression.sh` when you want a repeatable cross-project entry point.

Basic usage:

```bash
/home/admin101/.codex/skills/playwright-browser-regression/scripts/run_playwright_regression.sh \
  --project-dir /abs/path/to/frontend \
  --command "npm run regression:live-browser"
```

Useful options:

- `--smoke-command "npm run smoke:browser"`
  Run smoke first, then full regression.
- `--install-command "npm ci"`
  Install project dependencies first when `node_modules` is absent and the user wants that.
- `--skip-browser-install`
  Use only when the browser is already installed and you want to save time.

## Decision Rules

- Prefer bundled Chromium over `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.
- Prefer one browser session per run. Do not turn simple regression runs into long-lived services.
- Prefer the repo's existing auth/bootstrap flow. Do not hardcode usernames, passwords, or routes in the skill when the repo already owns them.
- If a project has both `smoke` and `regression`, run `smoke` first when you only need a fast health check.
- If browser binaries are missing, install with `npx playwright install chromium`.
- If Linux shared libraries are missing, fix host dependencies instead of switching to a system browser by default.

## When To Escalate

Escalate from "run existing regression" to "build or repair regression harness" only when:

- the repo has no browser command
- the existing command is clearly broken or stale
- the user explicitly wants a new regression harness

When escalating, keep the first pass small: login, one primary workflow, one responsive check, and console-error capture.

## References

- Read `references/linux-headless-notes.md` when the run is on Ubuntu/Linux and Playwright complains about missing system packages or sandbox/runtime issues.
