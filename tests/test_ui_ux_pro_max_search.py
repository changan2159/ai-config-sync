import importlib.util
import json
import sys
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parents[1] / "skills" / "shared" / "ui-ux-pro-max" / "scripts" / "search.py"
    spec = importlib.util.spec_from_file_location("ui_ux_pro_max_search", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_search_script_emits_json_matches(monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.setattr(sys, "argv", ["search.py", "fintech crypto", "--design-system", "-f", "json"])

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["focus"] == "design-system"
    assert payload["query"] == "fintech crypto"
    assert payload["matches"]


def test_search_script_handles_mixed_case_queries(monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.setattr(sys, "argv", ["search.py", "FinTech Crypto", "--design-system", "-f", "json"])

    module.main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["query"] == "FinTech Crypto"
    assert payload["matches"]


def test_search_script_persists_master_and_page_files(tmp_path: Path, monkeypatch, capsys) -> None:
    module = _load_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["search.py", "beauty spa wellness", "--design-system", "--persist", "-p", "Serenity Spa", "--page", "dashboard"],
    )

    module.main()

    master_path = tmp_path / "design-system" / "MASTER.md"
    page_path = tmp_path / "design-system" / "pages" / "dashboard.md"
    assert master_path.is_file()
    assert page_path.is_file()
    assert "beauty spa wellness" in master_path.read_text(encoding="utf-8")
    assert "Serenity Spa / dashboard" in page_path.read_text(encoding="utf-8")
    assert capsys.readouterr().out
