Repo-local `serena-agent` runtime for `ai-config-sync`.

This directory vendors the installed Python package payload needed by `serena-manager`:
- `serena`
- `interprompt`
- `solidlsp`

`tools/mcp/serena-agent.sh` bootstraps a local virtual environment from `requirements.lock`
and then runs `python -m serena.cli` with `PYTHONPATH` pointing at `pylib/`.
