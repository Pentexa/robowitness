"""Full verification-gate structural tests on an isolated temp DB (real simulation).

Asserts gate consistency rules, NOT a hard-coded verdict: VERIFIED requires all
gates PASS + 20/20 holdouts; any failed safety gate forces REJECTED; missing
coverage forces INCONCLUSIVE. Over-cautious candidate deterministically REJECTED.
"""
import json
from pathlib import Path
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.verification.holdout import evaluate_holdouts
from app.verification.paired import compute_policy_hash, compute_spec_hash

ROOT = Path(__file__).resolve().parent.parent.parent.parent
OVER_CAUTIOUS = PolicyConfig(id="candidate-overcautious-v1", max_speed_mps=0.05,
                             safe_distance_m=2.0, reaction_margin_m=1.0,
                             brake_gain=10.0, obstacle_prediction_horizon_s=2.0)


def _make_run(client, policy=None):
    spec = json.load(open(ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json"))
    r = client.post("/api/runs", json={"scenario": spec, "policy": (policy or {"id": "baseline-v1"})})
    assert r.status_code == 202
    return r.json()["job_id"], r.json()["result_id"]


def test_holdout_gate_requires_20_cases(tmp_path):
    manifest = {"scenarios": []}
    mp = tmp_path / "manifest.json"
    mp.write_text(json.dumps(manifest))
    res = evaluate_holdouts(PolicyConfig(), mp)
    assert res.status == "INCONCLUSIVE"
    assert "INSUFFICIENT_HOLDOUT_COUNT" in res.reason_codes


def test_paired_hashes_same_scenario_different_policy():
    spec = ScenarioSpec.model_validate_json(
        (ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json").read_text())
    assert compute_spec_hash(spec) == compute_spec_hash(spec)
    assert compute_policy_hash(PolicyConfig()) != compute_policy_hash(OVER_CAUTIOUS)


def test_full_verification_overcautious_rejected_with_all_gates(client):
    job_id, run_id = _make_run(client)
    svc = JobExecutionService()
    job = claim_next_job("test-worker")
    assert job is not None
    svc.execute_simulation_run(job)
    rv = client.post("/api/fixes/verify",
                     json={"baseline_run_id": run_id, "candidate_policy": OVER_CAUTIOUS.model_dump()})
    assert rv.status_code == 202
    vjob = claim_next_job("test-worker")
    svc.execute_verification(vjob)
    rec = client.get(f"/api/verifications/{vjob.result_id}")
    assert rec.status_code == 200
    body = rec.json()
    gate_ids = [g["gate_id"] for g in body["gates"]]
    assert gate_ids[:5] == ["GATE_1_REPRODUCE", "GATE_2_PAIRED", "GATE_3_HOLDOUT",
                            "GATE_4_REGRESSION", "GATE_5_INTEGRITY"]
    holdout = next(g for g in body["gates"] if g["gate_id"] == "GATE_3_HOLDOUT")
    assert holdout["details"]["total_cases"] == 20
    assert holdout["details"]["passed_cases"] == 20 or body["verdict"] == "REJECTED"
    # Verdict/gate consistency: any FAIL gate forbids VERIFIED; integrity must PASS
    statuses = [g["status"] for g in body["gates"]]
    if "FAIL" in statuses:
        assert body["verdict"] in ("REJECTED", "INCONCLUSIVE")
    if all(s == "PASS" for s in statuses):
        assert body["verdict"] == "VERIFIED_IN_SIMULATION"
    assert body["verdict"] == "REJECTED"  # over-cautious deterministically fails time gates
    ev = client.get(f"/api/evidence/{vjob.result_id}")
    assert ev.status_code == 200
    assert "hashes.json" in ev.json()["files"]
    dl = client.get(f"/api/evidence/{vjob.result_id}/download")
    assert dl.status_code == 200
    # Sealed paired-candidate replay served paginated from the package
    ct = client.get(f"/api/verifications/{vjob.result_id}/candidate-telemetry?offset=0&limit=50")
    assert ct.status_code == 200
    page = ct.json()
    assert page["total"] > 0 and len(page["frames"]) > 0
    assert page["frames"][0]["tick"] == 0
