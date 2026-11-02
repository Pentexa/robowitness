"""Ultra pack contract: baseline fails all five, the Meta-style patch passes.

These measured expectations are the demo's backbone (see
docs/HACKATHON_SUBMISSION.md): if a future law changes them, this test is
supposed to say so loudly instead of letting the demo quietly rot.
"""

import json
from pathlib import Path

from app.policies.configurable import configurable_policy
from app.policies.mpc_candidate import MpcCandidatePolicy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

ULTRA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scenarios" / "ultra"

BASELINE = PolicyConfig(
    id="baseline-v1",
    max_speed_mps=0.75,
    safe_distance_m=0.30,
    reaction_margin_m=0.05,
    brake_gain=1.5,
    obstacle_prediction_horizon_s=0.0,
)
META_PATCH = PolicyConfig(
    id="meta-patch",
    max_speed_mps=0.45,
    safe_distance_m=0.80,
    reaction_margin_m=0.20,
    brake_gain=3.0,
    obstacle_prediction_horizon_s=0.60,
)


def _run(spec, policy, fn):
    _, metrics, raw = SimulationRunner(spec, policy, fn).run()
    status, _ = evaluate_oracle(metrics, spec.oracle, raw)
    return status


def test_ultra_pack_all_five_present_and_valid():
    catalog = json.loads((ULTRA_DIR / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["entries"]) == 5
    for entry in catalog["entries"]:
        spec = ScenarioSpec.model_validate(
            json.loads((ULTRA_DIR / entry["file"]).read_text(encoding="utf-8"))
        )
        assert spec.id == entry["scenario_id"]


def test_baseline_fails_and_meta_patch_with_mpc_passes_all_ultra():
    catalog = json.loads((ULTRA_DIR / "catalog.json").read_text(encoding="utf-8"))
    for entry in catalog["entries"]:
        spec = ScenarioSpec.model_validate(
            json.loads((ULTRA_DIR / entry["file"]).read_text(encoding="utf-8"))
        )
        assert _run(spec, BASELINE, configurable_policy) == "FAIL", spec.id
        assert _run(spec, META_PATCH, MpcCandidatePolicy()) == "PASS", spec.id
