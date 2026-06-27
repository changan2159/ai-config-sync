---
name: database-workflow
description: Use when a task involves database schema lookup, SQL query drafting, PostgreSQL or SQL Server data inspection, view/procedure inspection, execution-plan or index analysis, routine insert/update/delete/exec work, or validating application behavior against database state. Prefer stable local wrapper commands when the host or project provides them; otherwise use the narrowest reliable native database CLI or reviewed project workflow.
---

# Database Workflow

Use this skill for database work in chat. It keeps database access consistent with this machine's wrapper tools, preserves JSON output for analysis, and applies the extra confirmation boundary only where destructive risk is real.

## Tool Defaults

Prefer stable local wrapper commands when they are already provided by the host or repository.
If the environment has reviewed database wrappers, use those first for consistent JSON-like or structured output.
If not, use the narrowest reliable native CLI or reviewed project workflow and say which path you used.

Typical wrapper shape:

```text
<db-wrapper> query "<sql>"
<db-wrapper> exec "<sql>"
```

Prefer wrappers or reviewed project-owned commands for:

- schema lookup
- data queries
- views, procedures, functions, and metadata inspection
- execution-plan collection when supported by the target database
- routine explicit writes

Use raw native CLI tools only when the wrappers cannot provide a needed capability, and say why.

## Safety Boundary

Direct writes are allowed when the user's intent is explicit and the operation is routine.

Ask for extra confirmation before clearly destructive or broad operations:

- `TRUNCATE`
- `DROP`
- `DELETE` without `WHERE`
- broad cleanup requests that may affect large datasets
- irreversible migrations or schema changes outside an explicit migration task

For updates and deletes, prefer previewing affected rows first when feasible:

```sql
SELECT COUNT(*) AS affected_rows
FROM ...
WHERE ...;
```

Do not hide uncertainty about environment, database, tenant, or target table. If the target is ambiguous, inspect metadata or ask a short clarifying question before writing.

## Workflow

1. Identify the database family: PostgreSQL or SQL Server.
2. Use wrapper-based metadata queries before assuming schema names, columns, or object types.
3. For data inspection, keep queries narrow and return only the columns needed for the task.
4. For performance analysis, collect the query text, predicates, joins, row estimates or actuals, and relevant indexes.
5. For writes, verify the target set, execute through the matching reviewed write path, then run a focused readback query.
6. Report the command class used, the important result, and any residual risk.

## Metadata Queries

PostgreSQL schema search:

```sql
SELECT table_schema, table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND (table_name ILIKE '%name%' OR column_name ILIKE '%name%')
ORDER BY table_schema, table_name, ordinal_position;
```

SQL Server schema search:

```sql
SELECT s.name AS schema_name, t.name AS table_name, c.name AS column_name, ty.name AS data_type
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.columns c ON c.object_id = t.object_id
JOIN sys.types ty ON ty.user_type_id = c.user_type_id
WHERE t.name LIKE '%name%' OR c.name LIKE '%name%'
ORDER BY s.name, t.name, c.column_id;
```

SQL Server procedure or view lookup:

```sql
SELECT s.name AS schema_name, o.name AS object_name, o.type_desc
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id = o.schema_id
WHERE o.type IN ('P', 'V', 'FN', 'IF', 'TF')
  AND o.name LIKE '%name%'
ORDER BY s.name, o.name;
```

## Performance Analysis

Focus on evidence rather than generic SQL advice.

Check:

- whether predicates are sargable
- whether joins match indexed keys
- whether row estimates differ sharply from actuals
- whether lookups, scans, sorts, hash matches, or spills dominate
- whether a proposed index duplicates an existing one
- whether write amplification or lock impact makes the index too costly

When recommending an index, include:

- target table
- key columns and included columns
- query or workload it helps
- tradeoff for writes/storage
- whether it needs production verification

## Output Expectations

- State which wrapper was used or why a raw tool was needed.
- Summarize the JSON result instead of pasting noisy output.
- Distinguish confirmed database facts from inferred application behavior.
- For writes, state the predicate, affected scope, and readback verification.
- For destructive requests requiring confirmation, stop before execution and ask directly.
