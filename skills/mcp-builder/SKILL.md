---
name: mcp-builder
description: Use when designing, implementing, reviewing, testing, or troubleshooting Model Context Protocol servers, clients, tools, resources, prompts, transports, schemas, auth, or MCP configuration for external service integration. Prefer this skill when Codex must create or modify MCP tool APIs rather than only configure an existing MCP server.
---

# MCP Builder

Use this skill to build MCP integrations that are useful to agents, not just thin wrappers around APIs.

## Design Workflow

1. Define the real user workflows the MCP server must enable.
2. Choose tool boundaries: workflow-level tools for common tasks, low-level tools for composability.
3. Design tool names with stable prefixes and action verbs.
4. Keep inputs structured and validate them with schemas.
5. Return focused results with pagination, filtering, and concise errors.
6. Decide transport: stdio for local tools, HTTP for remote services when deployment requires it.
7. Add tests or manual probes that exercise tool discovery, success responses, and actionable failures.

## Tool Quality Rules

- Prefer a small set of reliable, well-described tools over broad vague tools.
- Include enough metadata in responses for follow-up actions.
- Avoid returning huge raw payloads; support filters and pagination.
- Error messages should say what failed and what the agent can try next.
- Never expose secrets in tool descriptions, logs, or errors.
- Keep destructive tools explicit and require clear identifiers or confirmation flows at the client layer when possible.

## Implementation Notes

- For TypeScript, prefer the official MCP SDK unless the repo already has a different standard.
- For Python, prefer FastMCP when it matches the repo's environment.
- Follow existing repo patterns for config, logging, tests, and packaging.
- Use `mcp-configuration` or local machine rules only for configuring existing servers; use this skill for building or changing MCP server behavior.

## Output Expectations

- State the workflows and tool boundaries chosen.
- Document tool names, input schemas, response shapes, and auth assumptions.
- Include verification commands or manual MCP client checks.
- Mention remaining protocol, transport, or deployment risks.
