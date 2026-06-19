---
name: code-maintainability
description: "Use as the default maintainability gate during non-trivial coding, refactoring, or review work: reuse existing components, functions, methods, services, hooks, DTOs, queries, tests, and framework features; avoid duplicate logic, scattered call patterns, premature abstractions, and hard-to-change code. In brownfield development, start with a lightweight `architecture-deepening` owner/seam pass before editing, and escalate that skill when file bloat, shallow wrappers, duplicated orchestration, or unclear ownership become the main risk."
---

# Code Maintainability

Use this skill as the coding quality gate for reuse, abstraction, and long-term maintainability. It applies across frontend, backend, scripts, tests, configuration helpers, and integration code.

The goal is not to refactor everything. The goal is to make the requested change without adding avoidable duplication, file bloat, hidden coupling, or parallel patterns that future work must untangle.

## When To Use

Use this skill when:

- implementing a feature, behavior change, bug fix, or refactor that touches real product code
- adding a new component, function, method, service, hook, endpoint, DTO, query, command, test helper, or module
- editing a file that is already large, mixed-purpose, or hard to scan
- repeating similar logic, props, parameters, API calls, validation rules, data mappings, branching, error handling, or test setup
- deciding whether to extract, reuse, compose, split, or inline code
- reviewing code for maintainability risks

Skip it for one-line config edits, throwaway scripts, generated code, or tiny changes where reuse and abstraction are irrelevant.

If the main maintainability risk is file bloat, shallow wrappers, duplicated orchestration, or unclear ownership in brownfield code, pair this skill with `architecture-deepening`.

## Default Coding Gate

Before adding new code:

1. Search for existing behavior first.
   - Look for nearby components, functions, methods, services, hooks, DTOs, query helpers, validators, serializers, test fixtures, and framework utilities.
   - Prefer symbol-aware navigation when available; otherwise use `rg` and targeted file inspection.
2. Decide whether to reuse, extend, compose, or create.
   - Reuse when an existing abstraction already represents the concept.
   - Extend when the existing owner clearly owns the new variation.
   - Compose when shared pieces exist but the new flow has different orchestration.
   - Create only when reuse would blur ownership, add awkward flags, or couple unrelated flows.
3. Keep files cohesive.
   - Do not turn a file into a mixed-purpose dumping ground.
   - Split by responsibility when a file starts combining UI, data fetching, mapping, validation, state orchestration, side effects, and unrelated helpers.
   - Keep private helpers near their only caller; move shared helpers only when there is real reuse or a clear module boundary.
   - If a change risks making a file merely longer rather than more cohesive, switch to the `architecture-deepening` lens and identify the better owner before adding more code.
4. Control abstraction.
   - Extract duplicated logic when the duplication represents the same concept and is likely to change together.
   - Do not extract just because two blocks look similar but mean different things.
   - Avoid generic utility names such as `handleData`, `processItem`, `common`, or `utils` when a domain name is available.
5. Preserve call-site clarity.
   - Repeated call patterns should become a named helper, hook, service method, command, or factory when it makes the caller easier to read.
   - Avoid boolean-parameter APIs and option bags that hide multiple behaviors in one function.
   - Prefer small explicit functions over one configurable mega-function.
   - Do not extract pass-through wrappers that only rename an existing call unless they remove real caller knowledge or establish a real ownership seam.

## Reuse Targets

Check for these before creating a new thing:

- UI: design-system primitives, shared components, layout shells, form controls, table/list patterns, empty/error/loading states, icons, theme tokens
- Frontend logic: hooks, data-fetching clients, route helpers, state stores, schema validators, mappers, formatters
- Backend logic: services, domain methods, repositories, command/query handlers, validators, mappers, serializers, policy checks
- Data contracts: DTOs, request/response models, enums, schema definitions, generated clients, API conventions
- Tests: fixtures, builders, factories, fake clocks, test servers, auth helpers, database setup, assertion helpers
- Infrastructure: config loaders, logging helpers, retry/backoff policies, queue/job abstractions, framework built-ins

## File And Module Health

Treat these as warning signs:

- one file owns several unrelated responsibilities
- a component mixes layout, fetch calls, normalization, permissions, and mutation side effects
- a service accumulates unrelated methods because it was convenient
- private helpers become a long region below the main logic
- the same API call, validation rule, mapping, or permission check appears in multiple places
- tests duplicate large setup blocks instead of using a builder or fixture
- adding a small feature requires editing many unrelated call sites

When a warning sign is directly affected by the requested change, improve it in the smallest safe way. If fixing it would become a separate refactor, mention it instead of expanding the task silently.

When the warning sign is specifically "this file keeps growing while ownership stays muddy" or "new helpers are thin wrappers", use `architecture-deepening` to decide whether to deepen an existing owner, split out a domain-shaped owner, or leave an explicit debt note.

## Abstraction Heuristics

Use these defaults:

- two exact duplicates inside the same change can usually be extracted if the concept is identical
- three recurring copies across the codebase usually justify a shared abstraction
- one complex block may justify extraction if naming it makes the main flow easier to understand
- do not create a shared abstraction before understanding ownership and change direction
- do not add a broad base class, global utility, or shared module when a local helper or composition is enough

Prefer domain-shaped names:

- `buildInvoiceSummary` over `formatData`
- `useOrderFilters` over `useFilters`
- `createAuthenticatedApiClient` over `clientFactory`
- `mapCustomerToOption` over `mapToOption`

## Review Checklist

Before finishing non-trivial code work, check:

- Did I search for an existing implementation or pattern?
- Did I avoid duplicating business logic, UI structure, data mapping, validation, permissions, and test setup?
- Is each touched file still cohesive and scannable?
- Are new helpers placed at the narrowest useful scope?
- Are abstractions named after domain concepts rather than technical vagueness?
- Are repeated calls or option-heavy APIs clearer after the change?
- Did I avoid broad refactors unrelated to the user request?
- Did tests or verification cover the behavior rather than the private helper shape?
- If the touched file grew noticeably, did I confirm the change improved ownership rather than only adding more lines?

If any answer is no, fix it when the risk is local. Otherwise, call out the residual maintainability risk.
