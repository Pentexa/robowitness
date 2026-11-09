# API Reference

Interactive OpenAPI docs are served at `http://127.0.0.1:8000/docs` while the
backend runs. Auth is optional — see [`ENTERPRISE.md`](ENTERPRISE.md).

## Conventions

- Planar warehouse coordinates `[0, width_m] × [0, height_m]`; distances in
  meters, angles in radians, timestamps ISO 8601 UTC.
- Simulation ticks are integer counters at a fixed 1/60 s (60 Hz) step.
- Policies expose exactly five AI-adjustable numeric parameters:
  `max_speed_mps`, `safe_distance_m`, `reaction_margin_m`, `brake_gain`,
  `obstacle_prediction_horizon_s`. The AI never writes code or oracle rules.
- Scenario objects are circles (static or ping-pong). Controllers receive
  delayed, noisy sensor observations — never ground-truth poses.

## Endpoints

> Prefix: `/api`. Optional `X-API-Key` / `Idempotency-Key` headers.

### Health & Scenarios

| Method | Path | Purpose |
|:---:|---|---|
| GET | `/health` | Health + worker heartbeat + AI mode |
| GET | `/scenarios/reference` | Canonical `RW-REF-001` |
| GET | `/scenarios/library` | 20 scenarios (10 `RW-LIB-*`, 5 `RW-ULTRA-*`, 5 `RW-CROWD-*`) |
| POST | `/scenarios/generate` | AI-generated scenario (schema-validated) |
| POST | `/maps/scenario` | Occupancy-grid text → ScenarioSpec |
| POST | `/scenarios/from-image/detect` | SAM 3.1 segmentation of an uploaded still |
| POST | `/scenarios/from-image/scenario` | Selected boxes → runnable ScenarioSpec |
| GET | `/scenarios/from-image/saved` | Saved image scenarios |

### Runs & Jobs

| Method | Path | Purpose |
|:---:|---|---|
| POST | `/runs` | Queue a simulation run |
| GET | `/runs/{run_id}` | Run result, metrics, oracle verdict |
| GET | `/runs/{run_id}/telemetry` | Paginated replay frames |
| GET | `/jobs/{job_id}` | Job progress |
| POST | `/jobs/{job_id}/cancel` | Cancel a queued/running job |

### Investigation & Verification

| Method | Path | Purpose |
|:---:|---|---|
| POST | `/failures/{run_id}/investigate` | Grounded failure analysis (409 unless FAIL) |
| POST | `/fixes/verify` | Queue five-gate verification |
| GET | `/verifications` · `/verifications/{id}` | History; gate results & comparison |
| GET | `/verifications/{id}/candidate-telemetry` | Sealed candidate replay frames |
| GET | `/verifications/{id}/report.html` | Standalone HTML report |

### Evidence & Assets

| Method | Path | Purpose |
|:---:|---|---|
| GET | `/evidence/{id}` | Evidence manifest |
| GET | `/evidence/{id}/download` | Safe ZIP download |
| POST | `/evidence/inspect` | Independent ZIP re-verification |
| GET / POST | `/robots` | Robot catalog; create custom robots |
| GET / POST | `/policy-profiles` | Named 5-parameter presets |
| POST / GET | `/batteries` | Queue & list exam batteries |
| GET | `/batteries/{id}/report.md` | Markdown report card (`?lang=tr\|en`) |
| GET | `/batteries/trend` · `/batteries/compare?a=&b=` | Pass-rate history; A→B diff |
| POST | `/batteries/fleet` | One battery across multiple robots |
| POST / GET / DELETE | `/batteries/schedules` | Recurring batteries |
| POST / GET | `/imports/telemetry` · `/imports` | Real-drive log judging (CSV/JSON) |
| POST / GET | `/stress-tests` `{id}` | Latency × noise heatmap runs |
| POST / GET | `/adversarial-tests` `{id}` | Bounded AI-proposed rounds |
| GET | `/local-policies` | Opt-in user Python policies |
| GET | `/metrics` · `/prom` · `/audit` | Metrics, Prometheus, audit trail |

### Admin (optional enterprise layer)

| Method | Path | Purpose |
|:---:|---|---|
| POST / GET / DELETE | `/admin/api-keys` | DB-managed keys |
| POST / GET | `/admin/backup` · `/admin/backups` | WAL-safe SQLite backup |
| POST | `/admin/retention` | Delete old history (never sealed evidence) |
| POST | `/admin/restore` | Restore from backup |
| GET / POST | `/workspaces/export` · `/workspaces/import` | Tenant data bundle |
