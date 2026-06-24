---
name: fast-codebase-retrieval
description: Use when the user asks repository questions that are primarily about finding code, related files, owners, call chains, endpoints, composables, DTOs, services, wiring, or the smallest complete cross-file context in the current repo. This includes requests like analyzing the current repository, finding where something is implemented, tracing frontend/backend linkage, locating all related files, understanding project structure quickly, or retrieving code with high recall and low waste. Prefer this skill for brownfield retrieval-first tasks, especially when token efficiency and deep structure understanding both matter.
---

# Fast Codebase Retrieval

Use this skill for retrieval-first brownfield work where the main problem is not editing yet, but finding the right code and understanding the structure quickly without missing important related files.

Typical Chinese trigger intents:

- 分析当前仓库
- 找这段逻辑在哪
- 找相关文件
- 当前项目这个功能在哪里实现
- 帮我快速理解这个模块
- 找前后端对应代码
- 找调用链 / 入口 / owner
- 给我最小但完整的相关文件集合

## Goal

Produce a compact, high-signal file set and a reliable structure picture with the least wasted searching.

## Default Retrieval Order

1. Start with `CodeGraph` when the repo is indexed and the question has anchors.
2. Confirm with `Serena` for owners, symbols, references, implementations, and call chains.
3. Use `rg` for strings, config keys, routes, JSON fields, SQL, logs, generated names, and non-indexed assets.
4. Read source bodies only after the candidate set is small enough.

Do not treat `CodeGraph` as the final source of truth for edits.

## When To Trigger

Use this skill when the user asks things like:

- find all related files
- quickly understand this project or module
- trace who owns this behavior
- find the frontend/backed endpoints/composables/services involved
- give me the smallest complete file set for this feature
- use the fewest tokens but do not miss important related code
- analyze cross-file behavior in a large repo

## Query Strategy

Anchor early. Prefer:

- symbol names
- endpoint paths
- DTO or request/response type names
- file stems
- protocol, modality, feature, tenant, or domain terms already present in code

Avoid repeated broad natural-language queries. If the first query is noisy, tighten it immediately with explicit anchors.

## Operating Sequence

### 1. Frame the lookup

Classify the request first:

- symbol-driven: class, method, function, composable, service, orchestrator
- route-driven: endpoint, page, router path, handler
- data-driven: DTO, table, JSON field, config key, event name
- workflow-driven: "how does X happen", "who decides Y", "what files are involved"

### 2. Discover candidates fast

Use `CodeGraph` first when available for:

- likely owner files
- callers and callees
- nearby related symbols
- impact sets
- test anchors

If `CodeGraph` is unavailable, stale, or noisy, switch immediately to `Serena` plus `rg`.

### 3. Confirm structure

Use `Serena` to verify:

- the real owner symbol
- references and implementations
- call direction
- whether multiple similarly named files are actually separate flows

Prefer `get_symbols_overview`, `find_symbol`, and `find_referencing_symbols` before reading large files.

### 4. Fill blind spots

Use `rg` for things symbolic/indexed tools often miss:

- config and environment keys
- raw route fragments
- SQL and migration strings
- serialized JSON field names
- log messages
- comments that encode business constraints
- docs that define current behavior

### 5. Return a bounded result

Return:

- primary owner files
- secondary related files
- confirming tests if present
- one-sentence role for each file
- explicit note about ambiguity if two flows look similar

Prefer a small complete set over a long noisy list.

## Heuristics

- For “where is this implemented”, bias to owner files and direct callers.
- For “what do I need to change”, include owner files, contracts, wiring, and nearest tests.
- For “how does this workflow run”, include entrypoint, orchestrator/service, persistence/integration edge, and tests.
- For frontend/backend linkage, find page/composable/API client/endpoint/service chain, not just one side.
- When two candidate flows exist, say so explicitly instead of collapsing them into one answer.

## Stop Conditions

Stop expanding the search when all of these are true:

- the entry owner is identified
- the main branch points are identified
- the persistence or external boundary is identified when relevant
- the nearest validating tests are identified when present

If one of these is still missing, continue retrieval before answering.

## Failure Modes

- If `CodeGraph` results look stale, mention that manual `codegraph sync` may be required.
- If symbolic results are weak because the code is highly dynamic, say so and lean harder on `rg` plus direct reads.
- If the repo has multiple similar flows, present them as alternatives with the discriminator.

## Output Shape

Keep the answer compact and operational:

- `Primary files`: the minimum set that likely owns the behavior
- `Related files`: contracts, adapters, tests, or sibling flows worth checking
- `Why these`: one short sentence tying the chain together

Do not dump every matched file unless the user explicitly asks for exhaustive output.
