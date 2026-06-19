---
name: clarify-with-repo-context
description: Use when a request is ambiguous, under-specified, terminology-heavy, or likely to drift unless the agent first aligns on domain language, existing docs, constraints, and decision points. Explore the repo before asking questions, sharpen vague language, and persist durable terminology or workflow context in the project's approved locations.
---

# Clarify With Repo Context

Use this skill before planning or implementation when the request is still fuzzy enough that coding immediately would likely create rework.

## Core Rule

Do not ask the user questions that the repository can already answer.

Explore first. Ask only the questions that remain material after checking the code, docs, and existing AI guidance.

## Default Flow

1. Read the repo's authority sources first.
2. Identify the terms, assumptions, and decisions that are still ambiguous.
3. Challenge vague or overloaded language with concrete alternatives.
4. Ask the user one high-value question at a time when repo evidence is insufficient.
5. Once aligned, either hand off to planning/implementation or persist durable context.

## Authority Sources

Prefer the narrowest trustworthy source that already exists in the project:

- `AGENTS.md`
- `docs/ai/*`
- generated indexes such as `docs/ai/generated/*`
- existing code paths, module registrars, controllers, DTOs, tests, and config
- Serena memories when they exist for the active project

Do not introduce a parallel documentation structure when the repo already has one.

## What To Clarify

Look for ambiguity in:

- domain terms that may have multiple meanings
- user-visible behavior versus internal implementation guesses
- module ownership and extension points
- business rules, status transitions, permissions, and side effects
- required validation and acceptance criteria

When the user's wording conflicts with the code or docs, surface the conflict directly and ask which one is authoritative.

## Question Style

- Ask one question at a time when the answer affects the next question.
- Provide a recommended answer when the tradeoff is clear.
- Use concrete scenarios or examples instead of abstract wording.
- If a term is fuzzy, propose a canonical term and explain the distinction briefly.

Good pattern:

`The code treats X and Y as different concepts, but your request uses them interchangeably. Should this change apply to X only, Y only, or both?`

## Persistence

If the clarification uncovers durable project context, use `agents-self-evolution` thinking:

- short stable rule or index update: `AGENTS.md`
- deeper repo guidance: `docs/ai/*`
- dynamic or tentative context: Serena memory

Persist only verified or explicitly confirmed context. Record weak inferences as open questions, not facts.

## When Not To Use

Skip this skill when:

- the request is already precise and local
- the user explicitly wants direct implementation and the ambiguity is low-risk
- the repo cannot answer anything meaningful and a single blocking question is enough

## Handoff

After alignment, route to the next best skill:

- `writing-plans` for multi-step execution planning
- `test-driven-development` when behavior-first implementation is appropriate
- `systematic-debugging` when the real task is diagnosis
