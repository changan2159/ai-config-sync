---
name: codex-subagent
description: Use only when delegation is explicitly allowed and a task has a clear sidecar scope, read-only verifier pass, or parallel workstream with stable ownership boundaries. Do not treat general task complexity as a reason to spawn subagents; prefer this skill when prompt quality, bounded scope, read/write separation, or avoiding duplicated/conflicting work determines whether delegation is safe.
---

# Codex Subagent

Use this skill to decide whether to delegate work to a Codex subagent, then write prompts that are bounded enough to return useful results without polluting the main thread or causing conflicting edits.

## Decision Rule

Use a subagent when it will reduce main-thread context load or improve review quality.

Do not use a subagent just because the task is large, context-heavy, or important. The scope still needs to be independently executable and non-blocking to the immediate local step.

Good fits:

- read-only research that needs several searches or many files
- codebase mapping across a module the main agent does not need to read in full
- independent review of a proposed patch or fixed commit
- verification that can run without blocking the main integration step
- parallel work with non-overlapping file ownership

Stay local when:

- the task is short or one-file
- the next implementation step depends directly on the result
- the subagent would need unstable context from the current reasoning
- multiple agents would edit the same files or shared interface
- credentials, production systems, or destructive operations are involved

Use `parallel-execution` first when the decision is about multiple workstreams, ownership waves, or write boundaries. Use this skill for the mechanics and prompt quality of the Codex subagent itself.

## Execution Pattern

Prefer read-only subagents by default. Let the main agent own the critical path, file edits, integration, and final judgment.

For local Codex CLI delegation, use `codex exec` from the relevant workspace. In this desktop environment, keep prompts explicit about whether the subagent is read-only.

PowerShell shape:

```powershell
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check `
  -m <available-model> -c 'model_reasoning_effort="medium"' `
  "DETAILED_PROMPT_WITH_CONTEXT"
```

Use the current parent model only when the task requires multi-step reasoning or implementation-level judgment. For pure search or inventory, prefer a smaller/faster available model when one is configured.

Do not leave required subagent sessions running before final response. If a subagent command is long-running, poll it, summarize the returned evidence, and integrate the result.

## Prompt Template

Give the subagent enough context to succeed without leaking the answer you want.

```text
[TASK CONTEXT]
You are working in <absolute workspace path>. The task is <specific scope>.

[OBJECTIVES]
1. <concrete objective>
2. <concrete objective>

[BOUNDARIES]
- Mode: read-only | write allowed
- Owned paths: <files/directories, or "none">
- Do not modify: <shared interfaces, generated files, unrelated changes>
- Prefer: <tools/sources>

[OUTPUT FORMAT]
Return <exact format>: findings, file references, commands run, risks, or patch summary.

[SUCCESS CRITERIA]
Complete when <specific evidence has been gathered or check has passed>.
```

For cross-review, pass a fixed commit, exported patch, or explicit file list plus the smallest relevant surrounding context: callers, callees, tests, configuration, and commands. Do not rely on raw diff alone for behavioral or cross-module changes.

## Safety Rules

- Treat subagent output as evidence, not authority.
- Keep write access rare and only for clearly non-overlapping ownership.
- Never ask a subagent to run destructive filesystem, database, or production operations.
- Do not include secrets unless the user explicitly provided them for this purpose.
- Tell the subagent to preserve unrelated user changes.
- If the subagent reports uncertainty, carry that uncertainty into the final decision.

## Integration

After a subagent returns:

1. Extract the concrete evidence, file paths, commands, and risks.
2. Check whether its assumptions match the current workspace state.
3. Re-run or inspect only the focused evidence needed for confidence.
4. Apply or reject the recommendation locally.
5. Mention only meaningful subagent findings in the final answer.

## Output Expectations

- State whether delegation was used and why.
- Name the subagent scope and whether it was read-only.
- Summarize the evidence returned, not the entire transcript.
- Say how the result affected the implementation, review, or verification.
