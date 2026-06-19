---
name: security-review
description: Use when the user asks for a security audit, vulnerability review, secrets check, OWASP-style review, dependency vulnerability check, auth/authz review, injection/XSS/CSRF/path traversal assessment, sensitive data exposure review, or pre-release security pass. Prefer this skill over general code-review when security is the main objective or the code handles credentials, authentication, authorization, payments, PII, file uploads, command execution, database queries, or external webhooks.
---

# Security Review

Use this skill for evidence-backed security review. Report only concrete risks tied to code, configuration, dependency state, or observable behavior.

## Workflow

1. Define scope: files, modules, endpoint, PR diff, or full repository.
2. Identify stack and trust boundaries: auth provider, database, external APIs, file system, shell execution, browser boundary, and tenant/user boundaries.
3. Search for high-risk patterns before reading broadly.
4. Inspect the actual data flow from untrusted input to sensitive operation.
5. Run dependency or secret scans when the ecosystem provides a local command and it is safe.
6. Rank findings by exploitability and impact.

## Check Areas

- Authentication: session handling, token validation, password flows, MFA-sensitive operations, reset links, replay risk.
- Authorization: missing policy checks, IDOR, tenant isolation, role escalation, object ownership.
- Injection: SQL, command, template, LDAP/NoSQL, path traversal, unsafe deserialization, regex DoS.
- Browser security: XSS, CSRF, unsafe `innerHTML`, CSP gaps, insecure cookies, CORS over-breadth.
- Sensitive data: secrets in code, PII in logs, verbose errors, insecure storage, missing TLS assumptions.
- Dependencies: known vulnerable packages, abandoned packages on hot paths, unsafe transitive upgrades.
- Operations: debug flags, default credentials, missing rate limits, unbounded uploads or queries.

## Evidence Rules

- Include file and line references for each finding when possible.
- Do not report theoretical vulnerabilities without a plausible path.
- Distinguish confirmed vulnerabilities from hardening suggestions.
- Prefer existing project security patterns over generic prescriptions.
- For database inspection, use `database-workflow`.
- For broad independent review, use `codex-subagent` as a read-only verifier after defining scope.

## Output Expectations

- Findings first, ordered by severity: Critical, High, Medium, Low.
- Each finding includes impact, exploit path, and specific remediation.
- Include "No findings" only after stating what scope was actually reviewed.
- Mention scans or checks run and what they cover.
