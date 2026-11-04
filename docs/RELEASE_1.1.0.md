# RoboWitness 1.1.0 — Release Notes

Date: 2026-11-04. Minor release on top of 1.0.0: five measured feature
additions, one live-AI reliability fix, and a clearer verdict display.
The five-gate verification protocol, frozen holdout sets, and default
candidate law (`shared`) / sensor model (`legacy`) are unchanged.

## What's new

- **Sensor Stress Test** (`POST /api/stress-tests`, Stress Test tab):
  re-runs a scenario on a latency × noise grid (≤40 cells); every cell is a
  real recorded run judged by the same oracle, visualized as a heatmap.
- **AI Adversarial Testing** (`POST /api/adversarial-tests`, Test tab):
  Muse Spark proposes scenarios from measured failures in bounded rounds
  (config `RW_ADVERSARIAL_MAX_ITERATIONS`, hard cap 10); executed scenarios
  are real runs and the oracle decides. Live-measured 2026-11-04:
  `RW-AI-002` FAILED (0.0058 m), `RW-AI-003` PASSED (0.2688 m), 6,329 tokens.
- **Failure Timeline**: clearance, sensor delay, safety threshold, and
  failure events synchronized with the replay.
- **Evidence Inspector** (`POST /api/evidence/inspect`, Result tab):
  upload an evidence ZIP and independently re-verify SHA-256 integrity,
  missing files, and package type.
- **Portable HTML Report** (`GET /api/verifications/{id}/report.html`):
  standalone single-file report — gates, measured comparison, clearance
  chart, findings, evidence hashes.
- **Verdict display**: five-gate progress bar and measured chips
  (paired clearance, holdout count) under the final verdict.

## Fix

- **Live AI timeout**: default `RW_AI_TIMEOUT_SECONDS` 20 → 90. Measured:
  schema-bound reasoning calls can take ~30 s (3.4k tokens); at 20 s live
  generation intermittently degraded to `UNAVAILABLE`.

## Verification (measured at release time)

| Check | Result |
|---|---|
| Backend tests | 213/213 |
| Playwright E2E (live stack) | 24/24 |
| Live-stack journeys (`scripts/e2e_live_stack.py`) | ALL PASSED |
| Hackathon demo (`scripts/run_hackathon_demo.py`) | exit 0 |
| Live adversarial rounds (Muse Spark) | 2 rounds executed and judged |

## Container images

- `ghcr.io/pentexa/robowitness-backend:1.1.0`
- `ghcr.io/pentexa/robowitness-web:1.1.0`
