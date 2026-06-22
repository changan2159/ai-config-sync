from __future__ import annotations

from pathlib import Path

from serena_manager.state_store import StateStore


def test_load_quarantines_corrupt_meta_and_returns_none(tmp_path: Path) -> None:
    store = StateStore(tmp_path)
    project_root = tmp_path / "project"
    meta_dir = store.ensure_project_dir(project_root)
    meta_path = meta_dir / "meta.json"
    meta_path.write_text('{"project_root":"/tmp/demo"}}', encoding="utf-8")

    state = store.load(project_root)

    assert state is None
    assert not meta_path.exists()
    assert len(list(meta_dir.glob("meta.corrupt.*.json"))) == 1
