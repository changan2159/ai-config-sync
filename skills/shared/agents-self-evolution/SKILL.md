---
name: agents-self-evolution
description: Use when the user wants Codex to safely update AGENTS.md, Serena memories, skills, business logic documentation, project structure maps, glossary, workflows, or learned rules, or when a coding/debugging/review/refactor task uncovers durable project context, repeated corrections, verified commands, module boundaries, business rules, or workflow knowledge that should be persisted with minimal user interruption.
---

# Agents Self Evolution

这个 skill 用于沉淀和维护可复用的项目、团队、业务上下文，避免未来会话重复解释同一类规则、术语和约束。

它是当前这套 skills 中最典型的“业务沉淀型 skill”：机器触发层保持英文，涉及团队语义、业务规则、开放问题和 handoff 的内容可以明确使用中文优先。

## Purpose

Turn repeated corrections, stable preferences, project discoveries, and business knowledge into durable AI guidance without making the user restate context every time.

This skill favors autonomous low-risk updates, but prevents silent corruption of business facts, security rules, permissions, and production behavior.

## Quick Classification

在真正写入任何文档或 memory 之前，先做这个快速分类：

1. 这是不是 durable knowledge，而不是一次性任务细节？
2. 它属于哪一类？
   - project structure / ownership
   - business rule / domain understanding
   - terminology / glossary
   - workflow / operating sequence
   - verified command / build-test constraint
   - user preference / repeated correction
3. 最窄、最合适的落点在哪里？
   - `AGENTS.md`
   - `docs/ai-context/*`
   - Serena memories
4. 如果证据不足，它是不是应该降级为 candidate 或 open question？

## Auto Trigger Expectations

Treat this as a post-task persistence workflow, not only a manual documentation workflow.

After a non-trivial coding, debugging, review, or refactor task, run a short self-check:

- Did the task reveal stable project structure or ownership?
- Did it reveal a verified command, test path, or build constraint?
- Did it reveal a durable validation-harness convention such as solution name, fixture bootstrap rule, default test credentials, or smoke-test setup?
- Did it reveal durable business logic, terminology, or workflow knowledge?
- Did the user repeat a correction that should not be lost?

If the answer is yes, use this skill even when the user did not explicitly ask to update docs.
If the task only involved one-off implementation details with no durable learning, do not write noisy updates.

## Default Closing Action

At the end of every non-trivial task, run this default closing action:

1. Decide whether the task produced durable knowledge.
2. If yes, classify it as:
   - project structure / ownership
   - business rule / domain understanding
   - terminology / glossary
   - workflow / operating sequence
   - verified command / build-test constraint
   - user preference / repeated correction
3. Persist it in the narrowest correct place:
   - `AGENTS.md` for short constitutional rules and indexes
   - `docs/ai-context/business-domain.md` for verified business behavior
   - `docs/ai-context/project-structure.md` for structure and boundaries
   - `docs/ai-context/glossary.md` for terms
   - `docs/ai-context/workflows.md` for flows
   - Serena memories for dynamic corrections, observations, candidate rules, and evolution logs
4. If evidence is weak or inferred, record it as an open question instead of a fact.
5. Mention only meaningful persisted updates in the final response.

Default rule:

- If a task changes how future agents should understand the project, do not end the task without checking whether something should be persisted.

When you want a lower-freedom closeout flow, read `references/default-closing-checklist.md` and follow it step by step.

## Long-Task Handoff

When a task is not truly finished but has reached a natural pause, persist a minimal resume record.

Record:

- current phase or milestone
- current wave if parallel work was planned
- completed work
- remaining work
- blockers, risks, or assumptions that could mislead the next session
- the exact next recommended step

Prefer Serena memory for active handoff state unless the repository already has a reviewed location for AI task state.
Do not create a heavy planning filesystem by default just to save a short resume point.

## When To Use

Use this skill when:

- The user asks Codex to update, maintain, or evolve `AGENTS.md`.
- The user wants business logic, project structure, domain terms, or workflows captured for future AI work.
- The user repeatedly corrects the same behavior or business assumption.
- A task reveals durable project context that future agents should know.
- A skill, memory file, or AI context document should be created or refined.

Do not use this skill for one-off task context unless it is likely to recur.

## Storage Model

Prefer a layered knowledge system:

- `AGENTS.md`: Stable behavior constitution and index of where deeper context lives.
- `docs/ai-context/`: Project-local business and technical knowledge.
- Serena memories: Dynamic learned rules, corrections, observations, open questions, and evolution log.
- Skills: Reusable workflows or domain procedures that should trigger automatically.

Do not add `.serena/` to global or project ignore files. Serena project configuration and memories should stay portable with the repository when the project moves; if cache files need ignoring, use the narrowest cache-only path after inspecting the actual `.serena` layout.

For user-managed skills in this environment, treat `C:\Users\admin\.cc-switch\skills` as the single source of truth.
`C:\Users\admin\.codex\skills\<name>` may exist as symbolic-link mirrors that point back to `C:\Users\admin\.cc-switch\skills\<name>` for discovery.
Treat those mirrors as read-only pointers, not as separate editable copies.
Do not keep parallel standalone editable copies of the same user skill under `C:\Users\admin\.codex\skills` unless the user explicitly asks for that duplication.

Do not put all business logic into `AGENTS.md`. Keep `AGENTS.md` short and authoritative; link to deeper files.
Use Serena for dynamic memory whenever it is available in the active project. Use repo files only for knowledge that should be shared, reviewed, or versioned.

## Documentation Language Policy

When the user or project mainly operates in Chinese, prefer Chinese for:

- business logic documentation
- architecture explanations
- glossary entries
- workflow descriptions
- decisions and open questions

Keep these in their original machine-readable form:

- file paths
- class, interface, method, property, enum, table, and config key names
- commands and environment variables
- external package, tool, and protocol names

Preferred style:

- Chinese explanation first
- English/code identifier preserved inline with backticks
- First mention can use `中文名（CodeName）`

Do not translate machine identifiers into invented Chinese names.
If an existing project has a strong English-doc convention and the user has not asked for Chinese, follow the project convention instead.

## Encoding Policy

Use UTF-8 as the default encoding for all skill files, generated docs, scripts, validation helpers, and AI-maintained project context.

- Python scripts must pass `encoding="utf-8"` when reading or writing text.
- Prefer setting `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` in Windows user environments.
- Prefer PowerShell profiles that set `[Console]::InputEncoding`, `[Console]::OutputEncoding`, `$OutputEncoding`, and `chcp 65001`.
- Prefer Git global settings `i18n.commitEncoding=utf-8`, `i18n.logOutputEncoding=utf-8`, and `core.quotepath=false`.
- Do not rely on Windows default code pages such as GBK/CP936 for Chinese documentation.
- Only use GBK/CP936 when a legacy file or external system explicitly requires it, and document that exception near the command or file.
- If a third-party script fails on Chinese UTF-8 files, rerun it with UTF-8 mode or patch it to read text as UTF-8.

Recommended project layout:

```text
AGENTS.md
docs/
  ai-context/
    README.md
    project-structure.md
    business-domain.md
    glossary.md
    workflows.md
    data-model.md
    integration-map.md
    decisions.md
    open-questions.md
```

If a repository already has a docs or architecture convention, adapt to it instead of creating parallel documentation.

Recommended Serena memory names:

- `ai/corrections`
- `ai/observations`
- `ai/learned-rules`
- `ai/evolution-log`
- `ai/open-questions`
- `ai/handoffs`

When a project is available, prefer this Serena workflow:

1. Activate the project.
2. Check onboarding state.
3. Read or write Serena memories for dynamic context.
4. Use Serena symbol/search tools to verify structure and code ownership before documenting project structure.

## Update Classification

Classify every candidate update before editing.

### Auto-Apply

Apply directly when all are true:

- The rule is low-risk and reversible.
- The scope is clear.
- The source is explicit user instruction or directly observed repository fact.
- It does not broaden permissions or change safety posture.

Examples:

- User file-reference preferences.
- Known test/build commands verified locally.
- Stable smoke-test bootstrap conventions and validated default test credentials.
- Project directory map discovered from files.
- Repeated style corrections.
- Stable terminology confirmed by code, database schema, or docs.

### Candidate Only

Write a proposed update to Serena memory `ai/learned-rules`, `docs/ai-context/open-questions.md`, or a clearly marked candidate section when:

- The information is inferred from behavior, not directly stated.
- The update changes architecture guidance.
- The business rule affects customer-visible behavior.
- The rule may vary by module, tenant, region, environment, or product tier.
- Existing docs conflict.

### Ask First

Ask before writing when the update:

- Expands tool, filesystem, network, database, or production permissions.
- Weakens security, privacy, testing, review, or destructive-command policy.
- Changes deployment, migration, billing, auth, data retention, compliance, or credential handling behavior.
- Deletes or rewrites existing guidance from the user.
- Promotes an uncertain business inference into an authoritative rule.

## Fact vs Inference

对业务沉淀型 skill，最重要的不是“记得写”，而是“不要写错”。

按下面三层处理：

- Verified fact
  - explicit user instruction
  - direct repository fact
  - confirmed test, schema, API contract, or symbol result
- Candidate rule
  - repeated pattern with some evidence, but not yet fully confirmed
  - architecture or business interpretation that still may vary by module, tenant, or environment
- Open question
  - conflicting evidence
  - only one weak observation
  - anything that would be dangerous if promoted as fact

默认原则：

- 能写成 verified fact，就写事实
- 只能部分确认，就写 candidate
- 证据不足，就写 open question
- 不要把“看起来像规律”直接升级成权威规则

## Business Knowledge Rules

Business logic must be stored as evidence-backed facts, not vague summaries.

For each business rule, capture:

- `rule`: The concrete behavior.
- `scope`: Module, feature, tenant, role, region, environment, or data entity.
- `source`: User statement, code path, Serena symbol result, test, schema, API docs, ticket, or observed behavior.
- `confidence`: high, medium, or low.
- `updated`: Date of capture or latest confirmation.
- `owner`: Team/person if known, otherwise `unknown`.
- `exceptions`: Known carve-outs.
- `open questions`: Anything not verified.

Use this format:

```md
## Rule: <short name>

- rule: <concrete business behavior>
- scope: <where it applies>
- source: <evidence path, user statement, or observed command>
- confidence: <high|medium|low>
- updated: YYYY-MM-DD
- owner: <name|team|unknown>
- exceptions: <none|list>
- open questions: <none|list>
```

Never convert guesses into high-confidence business rules. If the source is only inference, set confidence to `low` and place it in Serena memory `ai/open-questions` or `open-questions.md` unless the user has allowed low-risk candidate notes.

## Project Structure Rules

For project structure, prefer objective maps over interpretation:

- Entry points: application startup, workers, CLIs, scheduled jobs.
- Module boundaries: folders/projects and their responsibilities.
- Dependency direction: which modules may call which.
- Registration points: DI, routing, plugins, event handlers, migrations.
- Test layout: where unit, integration, and E2E tests live.
- Generated code and ignored areas.

Update structure docs after direct inspection, not from memory.
When Serena is available, prefer `get_symbols_overview`, `find_symbol`, `find_referencing_symbols`, and `search_for_pattern` before falling back to broad text search.

## Evolution Workflow

1. Detect a durable learning opportunity.
2. Classify it as Auto-Apply, Candidate Only, or Ask First.
3. Pick the narrowest storage target.
4. Check existing guidance for duplicates or conflicts.
5. Write the smallest useful update.
6. Record the change in Serena memory `ai/evolution-log` when available.
7. In the final answer, mention only meaningful self-updates, not noisy details.

For substantial business documentation, prefer adding or updating `docs/ai-context/*` first, then add a short index link in `AGENTS.md`.
When creating or updating `docs/ai-context/*` for Chinese-language teams, write the prose in Chinese and preserve code anchors in English.

## Business-Oriented Output Expectations

When this skill is the primary skill, the output should make these boundaries obvious:

- what was promoted as a fact
- what stayed as candidate guidance
- what remained an open question
- where the information was written
- why that storage target was chosen

## Conflict Handling

When new information conflicts with existing guidance:

- Explicit user instruction in the current turn wins for the current task.
- Higher-scope `AGENTS.md` wins over Serena memory unless the user says otherwise.
- More specific project/module docs win over generic global preferences.
- Do not silently overwrite conflicts; create a candidate note or ask.

## Promotion Rules

Promote a candidate rule to `AGENTS.md` only when:

- It has been confirmed by the user, or
- It has been observed repeatedly in stable project artifacts, or
- It is required to prevent repeated costly mistakes.

Keep promoted rules short. Move detail into `docs/ai-context` or skills.

## References

- `references/agents-template.md`: Project `AGENTS.md` template.
- `references/ai-context-templates.md`: Business and project knowledge templates.
- `references/default-closing-checklist.md`: Low-freedom end-of-task persistence checklist.
- `references/update-rubric.md`: Detailed classification rubric.
- `references/serena-patterns.md`: Serena-first memory and structure workflow.

## Optional Script

Use `scripts/init_ai_context.py <project_root>` to create the recommended `docs/ai-context` skeleton in a project.
Use `scripts/audit_skills.py` to audit local skill directories for source-of-truth drift, duplicate user skills, missing `agents/openai.yaml`, and non-standard SKILL frontmatter.
