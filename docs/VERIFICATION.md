# Verification Protocol

Verification uses measured PyBullet telemetry and an independent oracle.
An AI proposal cannot assign or override the verdict. A successful verdict
applies to the recorded simulation configuration only.

## The Five Gates

1. **Reproduce the baseline failure** — with its frozen scenario and seed.
2. **Paired comparison** — baseline and candidate run with identical
   non-policy inputs; only the policy hash differs.
3. **Frozen holdout** — execute all 20 holdout scenarios; every case must pass.
4. **Regression suite** — critical scenarios still pass without degrading
   baseline-passing cases.
5. **Evidence sealing** — seal the complete package and independently verify
   its hashes.

A complete evaluation that violates a gate is `REJECTED`. Missing tests,
interrupted execution, invalid evidence, or unevaluable artifacts produce
`INCONCLUSIVE`. Only complete passing evidence permits
`VERIFIED_IN_SIMULATION`.

## Recorded Candidate Configuration

The recorded winning candidate uses `RW_CANDIDATE_LAW=mpc` (MPC-lite) and
policy `candidate-final-v1` ([implementation](../backend/app/policies/mpc_candidate.py)):

| Parameter | Value |
|---|---:|
| `max_speed_mps` | 0.60 |
| `safe_distance_m` | 1.00 |
| `reaction_margin_m` | 0.20 |
| `brake_gain` | 4.0 |
| `obstacle_prediction_horizon_s` | 1.00 |

MPC-lite evaluates 24 trajectory families over an ≈2.6-second horizon. The
default candidate law remains the shared law; MPC must be selected explicitly.
Baseline runs always use the shared law, so every frozen measurement is
unchanged.

The active [holdout manifest](../scenarios/holdout/manifest.json) contains 20
scenarios (`RW-HLD6-001`…`RW-HLD6-020`, recipe seed `20270214`). The candidate
was frozen before this set was generated. Earlier holds (v1–v5) were either
used for development or were rejected sets; they remain in `scenarios/holdout/`
for independent inspection.

## Recorded Outcomes

| Verification ID | Candidate | Verdict |
|---|---|---|
| `verif-6b2bfd8e0501` | MPC-lite on v6 | `VERIFIED_IN_SIMULATION` — 20/20 holdout, all gates pass |
| `verif-ec5ae352765d` | Shared law on v5 | `REJECTED` — 18/20 |
| `verif-1db21e6713ad` | Shared law on v6 | `REJECTED` — 18/20 |
| `verif-3b370a934cfc` | Over-cautious control | `REJECTED` |

These records describe specific runs, not guaranteed outcomes for arbitrary
AI suggestions. Any candidate must independently pass the full protocol.

## Reproduce

From the repository root, with backend dependencies installed and no competing
worker running:

```bash
RW_CANDIDATE_LAW=mpc python scripts/run_final_evaluation.py
python scripts/verify_evidence.py artifacts/verifications/<verification_id>
```

Windows PowerShell: `$env:RW_CANDIDATE_LAW = "mpc"`.

Inspect `holdout_results.json`, `regression_results.json`, `comparison.json`,
`manifest.json`, and `hashes.json` in the generated package. Run IDs are new on
each execution. No oracle threshold or frozen holdout may be changed to make a
candidate pass.
