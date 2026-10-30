"""Final evaluation driver: real API+service+worker code paths, real DB/artifacts.

Runs (all measured, verdicts computed by gates — never hard-coded):
  1. Baseline run job  -> POST /api/runs -> claim -> execute_simulation_run
  2. Verification of candidate-final-v1 (0.60/1.00/0.20/4.0/1.00)
  3. Verification of over-cautious (0.05/2.0/1.0/10.0/2.0) -> expect REJECTED
  4. Independent integrity re-check of every sealed package.

Candidate rationale (from reference physics only): 450ms latency makes
corridor-crossing timing critical; moderate speed + wide margins + prediction
horizon balances exposure time vs braking distance. Frozen at v1 before v2 eval.
"""
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from fastapi.testclient import TestClient
from app.db import init_db
from app.jobs.repository import claim_next_job
from app.jobs.service import JobExecutionService
from app.main import create_app
from app.evidence.integrity import verify_package_integrity
from app.evidence.recorder import RUN_REQUIRED_FILES, VERIFICATION_REQUIRED_FILES

FINAL_CANDIDATE = {
    "schema_version": "1.0",
    "id": "candidate-final-v1",
    "max_speed_mps": 0.60,
    "safe_distance_m": 1.00,
    "reaction_margin_m": 0.20,
    "brake_gain": 4.0,
    "obstacle_prediction_horizon_s": 1.00,
}
OVER_CAUTIOUS = {
    "schema_version": "1.0",
    "id": "candidate-overcautious-v1",
    "max_speed_mps": 0.05,
    "safe_distance_m": 2.0,
    "reaction_margin_m": 1.0,
    "brake_gain": 10.0,
    "obstacle_prediction_horizon_s": 2.0,
}


def main() -> int:
    init_db()
    app = create_app()
    client = TestClient(app)
    service = JobExecutionService()
    worker_id = "driver-final-eval"

    ref_spec = json.load(open(ROOT_DIR / "scenarios" / "reference" / "moving_obstacle_latency.json"))

    print("== 1. Baseline run ==", flush=True)
    r = client.post("/api/runs", json={"scenario": ref_spec, "policy": {"id": "baseline-v1"}})
    assert r.status_code == 202, r.text
    job_id, run_id = r.json()["job_id"], r.json()["result_id"]
    job = claim_next_job(worker_id)
    assert job and job.job_id == job_id, "atomic claim failed"
    service.execute_simulation_run(job)
    from app.db import get_db
    with get_db() as conn:
        row = conn.execute("SELECT oracle_status, reason_codes_json FROM runs WHERE run_id=?", (run_id,)).fetchone()
    print(f"   baseline run {run_id}: {row['oracle_status']} {row['reason_codes_json']}", flush=True)
    assert row["oracle_status"] == "FAIL", "Gate 1 requires a reproduced baseline FAIL"

    results = {}
    for name, cand in [("final-v1", FINAL_CANDIDATE), ("overcautious", OVER_CAUTIOUS)]:
        print(f"== 2. Verification: {name} ==", flush=True)
        rv = client.post("/api/fixes/verify", json={"baseline_run_id": run_id, "candidate_policy": cand})
        assert rv.status_code == 202, rv.text
        vjob_id, verif_id = rv.json()["job_id"], rv.json()["result_id"]
        vjob = claim_next_job(worker_id)
        assert vjob and vjob.job_id == vjob_id
        progress = []
        service.execute_verification(vjob, progress_callback=progress.append)
        with get_db() as conn:
            vrow = conn.execute(
                "SELECT verdict, gates_json, artifact_dir FROM verifications WHERE verification_id=?", (verif_id,)
            ).fetchone()
        gates = json.loads(vrow["gates_json"])
        print(f"   verification {verif_id}: verdict={vrow['verdict']}", flush=True)
        for g in gates:
            print(f"     {g['gate_id']}: {g['status']} {g.get('reason_codes', [])}", flush=True)
        ok, errs = verify_package_integrity(Path(vrow["artifact_dir"]), VERIFICATION_REQUIRED_FILES)
        print(f"   independent integrity re-check: ok={ok} errs={errs}", flush=True)
        assert ok, f"sealed package failed independent check: {errs}"
        results[name] = (verif_id, vrow["verdict"])

    print("== SUMMARY (measured) ==", flush=True)
    for name, (vid, verdict) in results.items():
        print(f"  {name}: {vid} -> {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
