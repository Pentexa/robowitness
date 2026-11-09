"""Crowd pack contract: baseline fails all, champion (MPC-crowd) passes all.

Frozen demo expectations — if a law or scenario changes them, this test
fails loudly on purpose (see scenarios/crowd/).
"""

import json
from pathlib import Path

from app.policies.configurable import configurable_policy
from app.policies.mpc_crowd import MpcCrowdPolicy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

CROWD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "scenarios" / "crowd"

BASELINE = PolicyConfig(
    id="baseline-v1",
    max_speed_mps=0.75,
    safe_distance_m=0.30,
    reaction_margin_m=0.05,
    brake_gain=1.5,
    obstacle_prediction_horizon_s=0.0,
)
CHAMPION = PolicyConfig(
    id="candidate-final-v1",
    max_speed_mps=0.60,
    safe_distance_m=1.00,
    reaction_margin_m=0.20,
    brake_gain=4.0,
    obstacle_prediction_horizon_s=1.00,
)


def _run(spec, policy, fn):
    _, metrics, raw = SimulationRunner(spec, policy, fn).run()
    status, _ = evaluate_oracle(metrics, spec.oracle, raw)
    return status


def test_crowd_pack_valid_and_baseline_fails_champion_passes():
    catalog = json.loads((CROWD_DIR / "catalog.json").read_text(encoding="utf-8"))
    assert len(catalog["entries"]) == 5
    for entry in catalog["entries"]:
        spec = ScenarioSpec.model_validate(
            json.loads((CROWD_DIR / entry["file"]).read_text(encoding="utf-8"))
        )
        assert _run(spec, BASELINE, configurable_policy) == "FAIL", spec.id
        assert _run(spec, CHAMPION, MpcCrowdPolicy()) == "PASS", spec.id


def test_crowd_law_is_opt_in_not_default():
    from app.config import settings
    from app.policies.candidate_law import get_candidate_policy_fn

    assert settings.RW_CANDIDATE_LAW == "shared"
    previous = settings.RW_CANDIDATE_LAW
    settings.RW_CANDIDATE_LAW = "mpc-crowd"
    try:
        assert isinstance(get_candidate_policy_fn(), MpcCrowdPolicy)
    finally:
        settings.RW_CANDIDATE_LAW = previous
