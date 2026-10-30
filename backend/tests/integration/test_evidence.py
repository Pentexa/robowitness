"""Evidence integrity tests: seal, tamper detection, missing members, path safety."""
import json
from pathlib import Path
from app.evidence.integrity import verify_package_integrity
from app.evidence.recorder import (
    RUN_REQUIRED_FILES,
    VERIFICATION_REQUIRED_FILES,
    save_run_artifacts,
    save_verification_artifacts,
)
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _tiny_spec() -> ScenarioSpec:
    """Minimal fast static scenario for evidence tests (no holdout dependency)."""
    return ScenarioSpec(
        id="RW-EVI-TINY", kind="static_obstacle", seed=7,
        world={"type": "warehouse", "width_m": 8.0, "height_m": 6.0,
               "duration_limit_s": 6.0, "fixed_timestep_s": 1.0 / 60.0},
        robot={"kind": "differential_drive",
               "start": {"x_m": 1.0, "y_m": 3.0, "yaw_rad": 0.0},
               "goal": {"x_m": 7.0, "y_m": 3.0},
               "goal_radius_m": 0.35, "body_radius_m": 0.25,
               "sensor_latency_ms": 0, "sensor_noise_std_m": 0.0},
        obstacles=[{"id": "S1", "shape": "circle", "radius_m": 0.3,
                    "motion": "static",
                    "start": {"x_m": 4.0, "y_m": 1.5}, "end": {"x_m": 4.0, "y_m": 1.5},
                    "speed_mps": 0.0}],
        oracle={"collision_free": True, "min_clearance_m": 0.25,
                "must_reach_goal": True, "max_duration_s": 6.0,
                "max_stuck_duration_s": 3.0},
    )


def test_run_package_seals_and_verifies(tmp_path):
    spec = _tiny_spec()
    policy = PolicyConfig()
    frames, metrics, reasons = SimulationRunner(spec, policy, configurable_policy).run()
    status, final = evaluate_oracle(metrics, spec.oracle, reasons)
    art = save_run_artifacts(tmp_path, "run-evi-test", spec, policy, frames, metrics, status, final)
    for req in RUN_REQUIRED_FILES + ["hashes.json"]:
        assert (art / req).exists()
    ok, errs = verify_package_integrity(art, RUN_REQUIRED_FILES)
    assert ok, errs


def test_byte_tampering_detected(tmp_path):
    spec, policy = _tiny_spec(), PolicyConfig()
    frames, metrics, reasons = SimulationRunner(spec, policy, configurable_policy).run()
    status, final = evaluate_oracle(metrics, spec.oracle, reasons)
    art = save_run_artifacts(tmp_path, "run-tamper", spec, policy, frames, metrics, status, final)
    with open(art / "metrics.json", "a", encoding="utf-8") as f:
        f.write(" ")
    ok, errs = verify_package_integrity(art, RUN_REQUIRED_FILES)
    assert not ok
    assert any("metrics.json" in e for e in errs)


def test_missing_member_detected(tmp_path):
    spec, policy = _tiny_spec(), PolicyConfig()
    frames, metrics, reasons = SimulationRunner(spec, policy, configurable_policy).run()
    status, final = evaluate_oracle(metrics, spec.oracle, reasons)
    art = save_run_artifacts(tmp_path, "run-missing", spec, policy, frames, metrics, status, final)
    (art / "telemetry.jsonl").unlink()
    ok, errs = verify_package_integrity(art, RUN_REQUIRED_FILES)
    assert not ok
    assert any("TELEMETRY" in e.upper() for e in errs)


def test_verification_package_tamper_detected(tmp_path):
    art = save_verification_artifacts(
        artifacts_root=tmp_path, verification_id="verif-tamper",
        manifest={"verification_id": "verif-tamper", "verdict": "REJECTED"},
        investigation={"hypothesis": "test"},
        comparison={"baseline": {}, "candidate": {}},
        holdout_results={"total_cases": 20, "passed_cases": 17},
        regression_results={"total_cases": 3, "passed_cases": 3},
        report_content="# test report",
    )
    ok, _ = verify_package_integrity(art, VERIFICATION_REQUIRED_FILES)
    assert ok
    (art / "report.md").unlink()
    ok2, errs2 = verify_package_integrity(art, VERIFICATION_REQUIRED_FILES)
    assert not ok2


def test_candidate_replay_sealed_and_endpoint_serves_or_404s(tmp_path, client):
    from app.schemas.telemetry import TelemetryFrame
    spec, policy = _tiny_spec(), PolicyConfig()
    frames, _, _ = SimulationRunner(spec, policy, configurable_policy).run()
    assert len(frames) > 0
    art = save_verification_artifacts(
        artifacts_root=tmp_path, verification_id="verif-replay",
        manifest={"verification_id": "verif-replay", "verdict": "REJECTED"},
        investigation={"hypothesis": "test"},
        comparison={"baseline": {}, "candidate": {}},
        holdout_results={"total_cases": 20, "passed_cases": 17},
        regression_results={"total_cases": 3, "passed_cases": 3},
        report_content="# test report",
        candidate_frames=frames,
    )
    assert (art / "telemetry_candidate.jsonl").exists()
    ok, _ = verify_package_integrity(art, VERIFICATION_REQUIRED_FILES)
    assert ok  # extra sealed member covered by hashes.json, required list unchanged
    # Legacy packages without candidate replay honestly report 404, not synthetic frames
    r = client.get("/api/verifications/verif-19161efb3b2c/candidate-telemetry")
    assert r.status_code in (200, 404)
