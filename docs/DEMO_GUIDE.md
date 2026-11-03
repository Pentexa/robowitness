# RoboWitness Demo Guide

Run the local backend, worker, and web application before following these workflows.

## 1. Demonstration Paths

### Explain the three model roles

- **Muse Wonder:** development/coding assistant used while building RoboWitness.
- **Muse Spark 1.3:** runtime scenario generation, measured-failure investigation
  and structured controller-parameter proposals.
- **SAM 3.1:** runtime camera/photo object segmentation; user-calibrated
  application code converts selected image boxes into simulation obstacles.

PyBullet executes the tests and the oracle/evidence gates determine verdicts.
Use the [model usage section](HACKATHON_SUBMISSION.md#where-and-how-we-used-the-three-meta-models)
for the exact inputs, outputs, API calls, source links and verification scope.

### Path A — Failure Detected
1. Select reference scenario `RW-REF-001` with moving obstacle and 450ms sensor latency.
2. Run baseline policy.
3. The baseline controller collides or violates minimum clearance due to observation delay.
4. Telemetry and oracle emit `COLLISION` or `MIN_CLEARANCE_VIOLATION` with exact failure tick.

### Path B — Improvement Accepted (recorded evaluation)
1. Trigger failure investigation.
2. Receive candidate parameter adjustment (e.g. reduced max speed, increased safe distance and prediction horizon).
3. Submit candidate for verification:
   - Gate 1: Baseline failure reproduced (`FAIL` at tick 358, `COLLISION`).
   - Gate 2: Paired comparison passes on identical seed.
   - Gate 3: **PASS 20/20** on a fresh, pre-registered v6 holdout set
     (recipe seed never used before; candidate law frozen before generation).
   - Gate 4: Critical regressions still pass (clear corridor, stationary obstacle, goal reachability).
   - Gate 5: Evidence sealed + independently re-verified.
   - Verdict: `VERIFIED_IN_SIMULATION` (`verif-6b2bfd8e0501`, MPC-lite receding-horizon law selected via `RW_CANDIDATE_LAW=mpc`).
   - Control case: the over-cautious candidate in the same run is honestly `REJECTED`.
4. History (kept for transparency): v1 was used for dev tuning (20/20, then archived);
   untouched eval sets scored v2 17/20, v3 17/20, v4 18/20, v5 18/20 — all `REJECTED`.
   The ceiling broke only when the structural MPC-lite planner replaced steering
   heuristics. Reproduce: with `RW_CANDIDATE_LAW=mpc`,
   `python scripts/run_final_evaluation.py` (real PyBullet DIRECT sims, live worker),
   then inspect `artifacts/verifications/<id>/holdout_results.json`. The
   [verification protocol](VERIFICATION_PROTOCOL.md) describes the retained
   evaluation sets, candidate configuration, and recorded outcomes.

### Path C — Candidate Rejected
1. Submit an over-conservative candidate (e.g. extremely low speed or excessive brake gain).
2. The candidate fails holdouts or goal deadline (`TIMEOUT` or `STUCK`).
3. Gate evaluation immediately reports `REJECTED` with specific failure reason codes.

### Path D — Photo to Scenario (camera/SAM, measured)
1. Upload a still (or capture a camera photo) in the Test tab's photo section.
2. Real SAM 3.1 segments the named concepts; select boxes, confirm scale + overhead view, place start/goal.
3. Preview shows the projected world; saving persists it for the current workspace.
4. The saved scenario runs through the ordinary run/verify flow — same oracle, same gates.

### 2. Viewing: 2D (canonical) and 3D (display only)
- The replay card offers **2D / 3D** toggle buttons (`btn-view-2d`, `btn-view-3d`).
- **2D canvas is the canonical evidence view** (exact telemetry coordinates).
- **3D (Three.js) is display only**: same frames, same poses — `x→X, y→Z`, fixed
  heights mirroring the PyBullet colliders (robot 0.3 m, obstacles 0.5 m, walls
  0.6 m). Physics, oracle and evidence are untouched by the camera.
- Full **3D physics** (ramps, 3D obstacles, non-planar robots) is explicitly out of
  scope: frozen fixtures, oracle geometry and all holdouts assume the planar
  warehouse (blueprint §1.1, §1.3).

## 3. Interactive Web Dashboard Workflow (English UI, Turkish switchable)
`Pick Scenario` -> `Run Baseline` -> `Replay Failure` -> `Inspect` -> `Review Fix` -> `Test the Fix` -> `Compare Runs` -> `Inspect Verdict` -> `Download Evidence ZIP` -> `Report Card` (exam battery) -> `Admin` (keys, schedules, metrics).
