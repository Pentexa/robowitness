"""Scenario library tests: every bundled case parses and carries metadata."""

import json
from pathlib import Path

from app.schemas.scenario import ScenarioSpec

LIB_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scenarios" / "library"


def test_library_endpoint_lists_ten_scenarios_with_metadata(client):
    res = client.get("/api/scenarios/library")
    assert res.status_code == 200
    entries = res.json()
    assert len(entries) == 10
    ids = [e["scenario"]["id"] for e in entries]
    assert len(set(ids)) == 10
    for entry in entries:
        assert entry["title"]
        assert entry["difficulty"] in ("Kolay", "Orta", "Zor")
        assert entry["category"]


def test_library_files_on_disk_all_validate():
    catalog = json.loads((LIB_DIR / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["entries"]) == 10
    for entry in catalog["entries"]:
        spec = ScenarioSpec.model_validate(
            json.loads((LIB_DIR / entry["file"]).read_text(encoding="utf-8"))
        )
        assert spec.id == entry["scenario_id"]


def test_library_includes_empty_control_and_dynamic_cases(client):
    entries = client.get("/api/scenarios/library").json()
    by_id = {e["scenario"]["id"]: e["scenario"] for e in entries}
    assert by_id["RW-LIB-009"]["obstacles"] == []
    assert any(s["kind"] == "dynamic_obstacle" for s in by_id.values())
    assert any(s["kind"] == "static_obstacle" for s in by_id.values())
