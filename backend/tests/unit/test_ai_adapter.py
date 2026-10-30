"""AI adapter tests: offline works without secrets; invalid output rejected; live unavailable."""
import pytest
from pydantic import ValidationError
from app.ai.adapter import MetaAdapter, OfflineReferenceAdapter, get_ai_adapter
from app.config import settings
from app.schemas.ai import InvestigationResponse
from app.schemas.policy import PolicyPatch
from app.schemas.scenario import ScenarioSpec


def test_offline_generate_returns_valid_spec():
    adapter = OfflineReferenceAdapter()
    spec, provenance = adapter.generate_scenario("narrow corridor, delayed sensing")
    assert provenance == "OFFLINE_REFERENCE"
    assert isinstance(spec, ScenarioSpec)
    # Re-validate through the canonical model (no special-casing allowed)
    ScenarioSpec.model_validate(spec.model_dump())


def test_offline_investigation_schema_and_patch_bounds():
    adapter = OfflineReferenceAdapter()
    inv, provenance = adapter.investigate_failure("baseline COLLISION at tick 358")
    assert provenance == "OFFLINE_REFERENCE"
    assert isinstance(inv, InvestigationResponse)
    assert inv.failure_tick >= 0
    assert isinstance(inv.suggested_patch, PolicyPatch)
    # Patch stays inside schema bounds
    p = inv.suggested_patch
    assert 0.05 <= (p.max_speed_mps or 0.75) <= 1.2


def test_forbidden_patch_keys_rejected():
    with pytest.raises(ValidationError):
        PolicyPatch.model_validate({"max_speed_mps": 0.5, "oracle_threshold": 0.1})
    with pytest.raises(ValidationError):
        PolicyPatch.model_validate({"exec_code": "import os"})


def test_malformed_scenario_rejected_not_executed():
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate({"id": "BAD", "kind": "dynamic_obstacle"})
    # NaN must never enter the pipeline
    with pytest.raises(ValidationError):
        ScenarioSpec.model_validate({
            "id": "RW-NAN", "kind": "static_obstacle", "seed": 1,
            "world": {"width_m": 10.0, "height_m": 6.0, "duration_limit_s": 10.0},
            "robot": {"start": {"x_m": float("nan"), "y_m": 4.0, "yaw_rad": 0.0},
                      "goal": {"x_m": 5.0, "y_m": 3.0}},
            "obstacles": [], "oracle": {"max_duration_s": 10.0},
        })


def test_meta_adapter_without_key_is_unavailable():
    adapter = MetaAdapter(api_key="", base_url="", model="")
    spec, prov = adapter.generate_scenario("anything")
    assert spec is None and prov == "UNAVAILABLE"
    inv, prov2 = adapter.investigate_failure("anything")
    assert inv is None and prov2 == "UNAVAILABLE"


def test_default_adapter_is_offline_without_credentials():
    assert settings.RW_META_API_KEY == "" or settings.RW_AI_MODE == "offline"
    adapter = get_ai_adapter()
    assert isinstance(adapter, OfflineReferenceAdapter)
