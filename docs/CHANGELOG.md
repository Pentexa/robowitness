# Changelog

All results recorded at release time. For future releases, optionally add
`docs/RELEASE_<version>.md` — the release workflow uses it as GitHub Release
notes (see `.github/workflows/release.yml`).

## 1.1.0 — 2026-11-04

Five feature additions on top of 1.0.0; verification protocol, holdout sets,
and default laws unchanged.

- **Sensor Stress Test** (`POST /api/stress-tests`): re-run a scenario on a
  latency × noise grid (≤40 cells); every cell is a real recorded run,
  visualized as a heatmap.
- **Adversarial Testing** (`POST /api/adversarial-tests`): AI proposes
  scenarios from measured failures in bounded rounds; the oracle judges every
  executed run.
- **Failure Timeline**: clearance, sensor delay, safety threshold, and
  failure events synchronized with the replay.
- **Evidence Inspector** (`POST /api/evidence/inspect`): independently
  re-verify uploaded evidence ZIPs (SHA-256, missing files, package type).
- **Portable HTML Report** (`GET /api/verifications/{id}/report.html`).
- Fix: live AI timeout raised 20 s → 90 s (`RW_AI_TIMEOUT_SECONDS`) after
  measured schema-bound reasoning calls took ~30 s.
- Images: `ghcr.io/pentexa/robowitness-{backend,web}:1.1.0`.

## 1.0.0 — 2026-11-02

First stable release after feature freeze.

- Verification core: deterministic PyBullet simulation, independent oracle,
  five gates, sealed evidence. First `VERIFIED_IN_SIMULATION`
  (`verif-6b2bfd8e0501`, MPC-lite on the pre-registered v6 holdout, 20/20).
- Product surface: robot catalog, scenario library + ultra + crowd packs,
  exam batteries with report cards, profile/custom robots, real-log judging,
  map import, passive ROS 2 recorder.
- Dashboard: English-first UI with Turkish switch, EN/TR leak guard, logo.
- Optional enterprise layer: API keys/JWT/OIDC, roles, workspaces, audit,
  metrics, Prometheus, webhooks, schedules, idempotency, backups/retention,
  export/import, CI gate, Docker Compose.
- Validation matrix (e2e of freeze): 159 backend tests ×2 environments,
  8 Playwright E2E, ruff/build/smoke clean, offline demo correct (baseline
  fail / candidate pass / over-cautious reject), compose 3/3 healthy.
- Two real bugs caught and fixed in fresh installs: undeclared `cryptography`
  dependency (OIDC) and missing `numpy` in the Docker image.
