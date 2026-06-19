# Update Rubric

Use this rubric to decide where a learned rule should go.

## Evidence Levels

High confidence:

- Direct user instruction.
- Existing authoritative project documentation.
- Passing tests that encode the behavior.
- Schema, migrations, validators, or code paths directly implementing the behavior.

Medium confidence:

- Multiple consistent code references.
- Existing UI/API behavior observed locally.
- Repeated user correction without contradictory evidence.

Low confidence:

- Inference from naming.
- Single ambiguous code reference.
- Unverified assumption from conversation.
- Behavior that may vary by tenant, region, environment, feature flag, or product tier.

## Target Selection

Use `AGENTS.md` for:

- Stable operating rules.
- Links to authoritative context.
- Verified commands and verification policy.
- Constraints every future task should respect.

Use `docs/ai-context/business-domain.md` for:

- Business rules.
- Invariants.
- Product behavior.
- Customer-visible workflows.

Use `docs/ai-context/project-structure.md` for:

- Repository layout.
- Entry points.
- Module boundaries.
- Registration points.
- Test locations.

Use `docs/ai-context/glossary.md` for:

- Domain terms.
- Abbreviations.
- Synonyms.
- Terms that must not be conflated.

Use `docs/ai-context/open-questions.md` for:

- Unverified assumptions.
- Conflicting evidence.
- Business behavior that needs confirmation.
- Any inference that could cause user-visible mistakes.

Use a skill for:

- Reusable procedures.
- Task workflows.
- Tool-specific behavior.
- Domain-specific steps that should trigger automatically.

Language selection for repo docs:

- Prefer Chinese when the user/team primarily uses Chinese.
- Keep identifiers, paths, commands, and code symbols in original English.
- Avoid translating technical anchors into natural-language aliases that cannot be mapped back to code.

Use Serena memories for:

- Dynamic corrections that may be promoted later.
- Observations from ongoing exploration.
- Learned rules that are not yet strong enough for `AGENTS.md`.
- Evolution log entries.
- Open questions and conflicting evidence that should stay out of authoritative docs.

## Anti-Patterns

Avoid:

- Adding every conversation detail to `AGENTS.md`.
- Promoting one-off user preferences to global behavior.
- Writing "always" rules from a single example.
- Recording business facts without source and confidence.
- Letting memory override explicit current user instructions.
- Duplicating the same dynamic note in both Serena and repo files without a clear reason.
- Silently deleting old guidance because a new fact appears to conflict.

## Minimal User Interruption

Default to these actions instead of asking:

- If low risk and verified, update directly.
- If useful but uncertain, write a candidate/open-question note.
- If too broad, narrow the scope before writing.
- If conflicting, preserve both and flag the conflict.

Ask only when the decision changes risk, permissions, security, production behavior, or authoritative business semantics.
