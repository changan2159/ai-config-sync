# Codex-Specific Additions

- When referencing local files in responses, prefer Markdown links so the user can click them in the Codex chat UI.
- Prefer repository-local `AGENTS.md`, project docs, and Serena memories for durable context according to their scope.
- Serena, CodeGraph, `fetch`, and `node_repl` are available in Codex sessions; for brownfield work follow the shared CodeGraph → Serena → text-search retrieval default, and confirm edit targets with Serena or direct reads rather than editing from discovery output alone.
- Use `codex-subagent` for bounded delegation or independent verification when the read and write boundary is clear.
- Prefer the `Product Design` plugin flow only when the user explicitly invokes that plugin or the task is clearly design-first rather than code-first.
- If CodeGraph retrieval looks stale, manual `codegraph sync` may be required in sessions where watch is intentionally disabled.

# Codex Verification Additions

- When a child verifier agent is available, prefer it as the first-pass independent reviewer before reaching for the `code-review` skill or a manual diff review.

# Codex Review Commands

- Prefer the child verifier path first; if that is unavailable, reuse the verified non-interactive CLI commands on this host, keep the review prompt tightly scoped, and avoid improvising flags.
- `Codex CLI` native review shape: `cat /tmp/review-prompt.txt | codex review --uncommitted`
- `Claude CLI` health probe when reliability matters: `claude -p --bare --no-session-persistence --permission-mode dontAsk --output-format json "Reply with exactly OK."`
- `Claude CLI` substantive review shape: `cat /tmp/review-prompt.txt | claude -p --bare --no-session-persistence --permission-mode dontAsk --input-format text --output-format json`
- Treat `Claude CLI` as failed for review purposes if it exits `0` but returns an empty `result`.
- `OpenCode CLI` cross-review shape: `opencode run "$(cat /tmp/review-prompt.txt)" --format json`
- For `OpenCode CLI`, read the final review text from the emitted JSON event stream; the assistant verdict appears in the last event object with `"role": "assistant"` or the equivalent content event; do not mistake intermediate tool-call or tool-result events for the actual verdict.
