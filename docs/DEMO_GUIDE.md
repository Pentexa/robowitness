# RoboWitness Demo Guide

Governed by Section 1.2 and Section 11 of `ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md`.

## 1. Demonstration Paths

### Path A — Failure Detected
1. Select reference scenario `RW-REF-001` with moving obstacle and 450ms sensor latency.
2. Run baseline policy.
3. The baseline controller collides or violates minimum clearance due to observation delay.
4. Telemetry and oracle emit `COLLISION` or `MIN_CLEARANCE_VIOLATION` with exact failure tick.

### Path B — Improvement Under Evaluation (currently UNMET — honest status)
1. Trigger failure investigation.
2. Receive candidate parameter adjustment (e.g. reduced max speed, increased safe distance and prediction horizon).
3. Submit candidate for verification:
   - Gate 1: Baseline failure reproduced (`FAIL` at tick 358, `COLLISION`).
   - Gate 2: Paired comparison passes on identical seed.
   - Gate 3: **Not yet satisfied.** Best results per frozen set:
     `candidate-final-v1` (brake-only) → v1-dev 20/20, v2-eval 17/20;
     `candidate-final-v2` (brake-only) → v3-eval 17/20;
     `candidate-final-v3` (velocity-track avoidance law) → 60-case dev 59/60, v4-eval **18/20**
     (HLD4-008 clearance+stuck, HLD4-016 stuck-flag).
   - Verdict is therefore honestly `REJECTED`, never manufactured `VERIFIED_IN_SIMULATION`.
4. Finding: reactive control (brake-only, then brake + horizon-gated lateral avoidance
   from delivered velocity tracks) has a capability ceiling on fast-obstacle /
   high-latency crossing geometries: stronger avoidance displaces collisions into
   stuck/timeout failures. A VERIFIED verdict needs either a richer controller family
   (e.g. committed global re-planning — out of MVP scope) or a narrower holdout ODD
   (a product decision, not taken silently here).
5. Reproduce: `python scripts/run_final_v3.py` (real PyBullet DIRECT sims, live worker),
   then inspect `artifacts/verifications/<id>/holdout_results.json`. Every tuning step
   is scripted under `scripts/`; every evaluation ran on a set the candidate never saw
   (v1 dev → v2/v3/v4 eval, archived byte-exact).

### Path C — Candidate Rejected
1. Submit an over-conservative candidate (e.g. extremely low speed or excessive brake gain).
2. The candidate fails holdouts or goal deadline (`TIMEOUT` or `STUCK`).
3. Gate evaluation immediately reports `REJECTED` with specific failure reason codes.

### 2. Viewing: 2D (canonical) and 3D (display only)
- The replay card offers **2D / 3D** toggle buttons (`btn-view-2d`, `btn-view-3d`).
- **2D canvas is the canonical evidence view** (exact telemetry coordinates).
- **3D (Three.js) is display only**: same frames, same poses — `x→X, y→Z`, fixed
  heights mirroring the PyBullet colliders (robot 0.3 m, obstacles 0.5 m, walls
  0.6 m). Physics, oracle and evidence are untouched by the camera.
- Full **3D physics** (ramps, 3D obstacles, non-planar robots) is explicitly out of
  scope: frozen fixtures, oracle geometry and all holdouts assume the planar
  warehouse (blueprint §1.1, §1.3).

## 3. Interactive Web Dashboard Workflow
`Choose Scenario` -> `Run Baseline` -> `Replay Failure` -> `Investigate` -> `Review Candidate` -> `Verify Candidate` -> `Compare Runs` -> `Inspect Verdict` -> `Download Evidence ZIP`.
