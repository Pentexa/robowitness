# RoboWitness Demo Guide

Governed by Section 1.2 and Section 11 of `ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md`.

## 1. Demonstration Paths

### Path A — Failure Detected
1. Select reference scenario `RW-REF-001` with moving obstacle and 450ms sensor latency.
2. Run baseline policy.
3. The baseline controller collides or violates minimum clearance due to observation delay.
4. Telemetry and oracle emit `COLLISION` or `MIN_CLEARANCE_VIOLATION` with exact failure tick.

### Path B — Improvement Accepted
1. Trigger failure investigation.
2. Receive candidate parameter adjustment (e.g. reduced max speed, increased safe distance and prediction horizon).
3. Submit candidate for verification:
   - Gate 1: Baseline failure reproduced.
   - Gate 2: Paired comparison confirms candidate avoids failure on identical seed.
   - Gate 3: 20 frozen holdout scenarios all pass.
   - Gate 4: 3 critical regressions all pass without degradation.
   - Gate 5: Evidence sealed with SHA-256 hashes.
4. Final verdict: `VERIFIED_IN_SIMULATION`.

### Path C — Candidate Rejected
1. Submit an over-conservative candidate (e.g. extremely low speed or excessive brake gain).
2. The candidate fails holdouts or goal deadline (`TIMEOUT` or `STUCK`).
3. Gate evaluation immediately reports `REJECTED` with specific failure reason codes.

## 2. Interactive Web Dashboard Workflow
`Choose Scenario` -> `Run Baseline` -> `Replay Failure` -> `Investigate` -> `Review Candidate` -> `Verify Candidate` -> `Compare Runs` -> `Inspect Verdict` -> `Download Evidence ZIP`.
