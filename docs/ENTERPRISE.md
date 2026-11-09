# Enterprise Guide (Optional)

Every feature here is opt-in. With nothing configured, the system works as a
single-user open local mode.

## Auth, Roles & Workspaces

```
.env: RW_API_KEYS=key1:admin:ws-a;key2:editor:ws-a;key3:viewer:ws-a
```

- Keys are empty → open local mode. Keys are set → all `/api` routes except
  `/health` require `X-API-Key`. Roles: `admin > editor > viewer`.
- User robots, policy profiles, batteries, and imports are isolated per
  workspace; built-in catalogs are shared. Without keys, the
  `X-Workspace-Id` header does the same.
- JWT: `Authorization: Bearer <token>` with `RW_JWT_SECRET` (HS256) or
  `RW_OIDC_JWKS_URL` (+ optional issuer/audience) for RS256/OIDC. Claims:
  `sub` → actor, `role` → role, `workspace` → workspace.

## Audit & Metrics

- Every write is recorded (actor, role, workspace, path, status).
  `GET /api/audit?limit=50` (admin), `GET /api/metrics`.
- Prometheus exposition: `GET /api/prom` (public, like health).

## Batteries, Maps & Imports

- `GET /api/batteries/compare?a=<id>&b=<id>` — per-scenario
  improved/worsened diff; `GET /api/batteries/trend` — pass-rate history;
  `POST /api/batteries/fleet` — one battery across multiple robots
  (incompatible robots skipped with reasons).
- `POST /api/maps/scenario` — occupancy-grid text (`#` obstacle, `S` start,
  `G` goal) + cell size → validated scenario (≤8 circle obstacles).
- `POST /api/scenarios/from-image/detect` + `/from-image/scenario` — photo →
  SAM 3.1 detections → runnable scenario (requires confirmed scale and
  overhead view). Photos are never stored; only boxes + source SHA-256.

## Schedules, Idempotency, Webhooks

- `POST /api/batteries/schedules` (≥5 min interval) — the worker enqueues due
  batteries once.
- `POST /api/runs` and `/api/batteries` honor `Idempotency-Key` (same request
  returns the same job).
- `RW_WEBHOOK_URL` + `RW_WEBHOOK_SECRET` — HMAC-SHA256-signed completion
  notifications (`X-RoboWitness-Signature`).
- Rate limiting per actor: `RW_RATE_LIMIT_PER_MIN` (429).

## Backups & Retention

- `POST /api/admin/backup` — consistent SQLite backup + SHA-256.
- `POST /api/admin/retention` (`older_than_days`, dry-run by default) —
  removes old battery/log/audit history; never touches sealed evidence.
- `POST /api/admin/restore` — safety copy first, then restore.
- `GET/POST /api/workspaces/export` / `/import` — full tenant JSON bundle.

## CI Gate

```bash
python scripts/ci_battery_gate.py --robot robot-turtlebot3-waffle-pi \
  --policy-file policy.json --min-pass-rate 0.8 --max-collisions 0
```

Exit 0 = gate passed, 1 = thresholds missed, 2 = infrastructure error.
Requires a running worker. Threshold logic lives in
`app/verification/battery_gate.py` and is unit-tested.

## Stress, Adversarial, Inspector, Reports

- `POST /api/stress-tests` — re-runs a scenario on a latency × noise grid
  (≤40 cells); every cell is a real recorded run.
- `POST /api/adversarial-tests` — AI proposes scenarios from measured
  failures (default 5 rounds, hard cap 10); the oracle judges every run.
  For live AI, `RW_AI_TIMEOUT_SECONDS=90` is recommended.
- `POST /api/evidence/inspect` — path-traversal-safe ZIP inspection with
  full SHA-256 re-verification.
- `GET /api/verifications/{id}/report.html` — standalone single-file report.
- Sensor models (`RW_SENSOR_MODEL`): `legacy` (default) or `beam`
  (24-ray LiDAR-like casting). All frozen results were measured in legacy.

## Docker

```bash
docker compose up --build   # backend + worker + web, artifacts in named volume
```

## Honest Limits

- SQLite is a single file: logical workspace isolation, no sharding.
- Physics stays kinematic and 2D (occlusion + optional 24-ray mode).
- Report cards and HTML reports are not real-world safety approvals; a
  verified verdict means verified in simulation, under the recorded
  configuration.
