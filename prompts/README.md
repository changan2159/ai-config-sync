Repository-managed prompt sources live here.

- `shared-global-prompt.md` is the shared core copied into every managed client prompt target.
- `shared-global-prompt.md` should stay short, constitutional, and genuinely cross-client. Put branching workflow logic into shared skills instead of bloating the always-on prompt.
- Detailed frontend layout, spacing, hierarchy, and product-UX heuristics belong in `frontend-design` and related UI skills, not in the always-on shared core.
- `*-global-prompt.md` overlays are appended per client during sync.
- Client overlays should contain client-specific syntax, capabilities, verifier paths, or memory behavior; keep shared routing and generic coding policy in the shared core or shared skills.
