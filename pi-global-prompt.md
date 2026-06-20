## Pi-Specific Notes

- Shared skills are synced into `~/.pi/agent/skills-shared` and loaded through `~/.pi/agent/settings.json`.
- Shared MCP servers are synced into `~/.config/mcp/mcp.json` and exposed through the installed `pi-mcp-adapter` package.
- Prefer the shared synced skills and MCP tools before inventing duplicate local workflows.
- Restart `pi` or run `/reload` after changing synced prompt, settings, or project skill files.
