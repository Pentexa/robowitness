# RoboWitness Verification Protocol

Verification uses measured PyBullet telemetry and an independent oracle.
An AI proposal cannot assign or override the verdict. A successful verdict
applies to the recorded simulation configuration only.

## Required gates

1. Reproduce the original baseline failure with its frozen scenario and seed.
2. Run baseline and candidate independently with identical non-policy inputs.
3. Execute all 20 frozen holdout scenarios; every required case must pass.
4. Pass the critical regression scenarios without degrading baseline-passing cases.
5. Seal the complete evidence package and independently verify its hashes.

A complete evaluation that violates a gate is `REJECTED`. Missing tests,
interrupted execution, missing telemetry, or invalid evidence prevent a successful
verdict and produce `INCONCLUSIVE` where the required evidence is unevaluable.
Only complete passing evidence permits `VERIFIED_IN_SIMULATION`.

## Recorded candidate and evaluation data

The recorded MPC-lite candidate uses `RW_CANDIDATE_LAW=mpc` and policy
`candidate-final-v1` with these parameters:

| Parameter | Value |
|---|---:|
| `max_speed_mps` | 0.60 |
| `safe_distance_m` | 1.00 |
| `reaction_margin_m` | 0.20 |
| `brake_gain` | 4.0 |
| `obstacle_prediction_horizon_s` | 1.00 |

The MPC-lite implementation is [mpc_candidate.py](../backend/app/policies/mpc_candidate.py).
It evaluates 24 trajectory families over an approximately 2.6-second horizon.
The baseline law and its parameters are unchanged. The default candidate law
remains the shared law; MPC must be selected explicitly.

The active [holdout manifest](../scenarios/holdout/manifest.json) contains
20 scenarios, IDs `RW-HLD6-001` through `RW-HLD6-020`, starting at seed 7001.
Its recipe is `frozen_holdout_v6`, with recipe seed `20270214`. The candidate
was frozen before this set was generated on 2026-11-02.

The v1, v2, v3, and v5 sets were used to develop the MPC law and are therefore
development data, not independent evidence for the v6 result. The v5 geometry
duplicated v4; v6 uses a previously unused recipe seed. Earlier manifests remain
in `scenarios/holdout/` so this distinction can be independently inspected.

## Recorded outcomes

- `verif-6b2bfd8e0501`: MPC-lite, `VERIFIED_IN_SIMULATION`, all five gates
  passing and 20/20 v6 holdouts. The sealed package was independently rechecked.
- `verif-ec5ae352765d`: the previous shared-law candidate on v5, `REJECTED`,
  18/20 holdouts. Cases `RW-HLD5-008` and `RW-HLD5-016` failed.
- `verif-1db21e6713ad`: a separate v6 shared-law run claimed by the live worker,
  `REJECTED`, 18/20. This is distinct from the single registered MPC evaluation.
- `verif-3b370a934cfc`: the over-cautious control candidate, `REJECTED`.

These records describe specific runs, not guaranteed outcomes for arbitrary
AI suggestions. Any candidate must independently pass the same complete protocol.

## Reproduce and inspect

With the backend dependencies installed, run from the repository root using
the documented local configuration. Avoid competing workers during this
in-process evaluation:

```powershell
$env:RW_CANDIDATE_LAW = "mpc"
python scripts/run_final_evaluation.py
python scripts/verify_evidence.py artifacts/verifications/<verification_id>
```

Inspect `holdout_results.json`, `regression_results.json`, `comparison.json`,
`manifest.json`, and `hashes.json` in the generated package. Run IDs are new on
each execution. No oracle threshold or frozen holdout may be changed to make
a candidate pass.
