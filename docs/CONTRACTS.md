# RoboWitness Canonical Data Models & API Contracts

This document describes RoboWitness's canonical data models and API contracts.

## 1. Geometry & Coordinate Space
- Planar warehouse coordinate system: `[0, width_m] x [0, height_m]`
- Angles: radians `[-pi, pi)`
- Distances: meters
- Timestamps: ISO 8601 UTC with `Z` suffix
- Simulation ticks: Integer tick counter at `fixed_timestep_s = 1/60` (60 Hz)

### Primitive Types
- `Point2D`: `(x_m: float, y_m: float)`
- `Pose2D`: `(x_m: float, y_m: float, yaw_rad: float)`
- `Vector2D`: `(x_mps: float, y_mps: float)`

## 2. Scenario Specification (`ScenarioSpec`)
- `schema_version`: Literal `"1.0"`
- `id`: Unique string, e.g., `"RW-REF-001"`
- `kind`: `"static_obstacle"` | `"dynamic_obstacle"`
- `seed`: Integer `0..2^32-1`
- `world`:
  - `type`: `"warehouse"`
  - `width_m`: `6.0..20.0`
  - `height_m`: `4.0..15.0`
  - `duration_limit_s`: `5.0..60.0`
  - `fixed_timestep_s`: `1/60`
- `robot`:
  - `kind`: `"differential_drive"`
  - `start`: `Pose2D`
  - `goal`: `Point2D`
  - `goal_radius_m`: `0.20..0.60`
  - `body_radius_m`: `0.15..0.40`
  - `wheel_base_m`: float
  - `wheel_radius_m`: float
  - `sensor_range_m`: float
  - `sensor_latency_ms`: `0..1000`
  - `sensor_noise_std_m`: `0.0..0.2`
- `obstacles`: List of circular obstacles:
  - `id`: String identifier
  - `shape`: `"circle"`
  - `radius_m`: `0.15..0.80`
  - `motion`: `"static"` | `"ping_pong"`
  - `start`: `Point2D`
  - `end`: `Point2D`
  - `speed_mps`: `0.0..1.5`
- `oracle`:
  - `collision_free`: boolean
  - `min_clearance_m`: `0.0..1.0`
  - `must_reach_goal`: boolean
  - `max_duration_s`: float <= duration_limit_s
  - `max_stuck_duration_s`: float (e.g., 3.0s)

## 3. Policy Configuration (`PolicyConfig`)
Only 5 AI-adjustable numeric parameters:
- `schema_version`: Literal `"1.0"`
- `id`: String assigned by system (e.g., `"baseline-v1"`)
- `max_speed_mps`: `0.05..1.20`
- `safe_distance_m`: `0.20..2.00`
- `reaction_margin_m`: `0.00..1.00`
- `brake_gain`: `0.10..10.00`
- `obstacle_prediction_horizon_s`: `0.00..2.00`

### Shared navigation law (baseline runs ALWAYS use this algorithm)

Proportional heading to goal + braking on delayed sensor distance + horizon-gated
lateral avoidance. Only the five numeric fields above may differ between runs.

### Candidate laws (explicit opt-in via `RW_CANDIDATE_LAW`, default `shared`)

The verified configuration is **MPC-lite** (`mpc`): receding-horizon rollouts
over delivered velocity tracks with a preferred-clearance tier — the law that
earned `VERIFIED_IN_SIMULATION` on the pre-registered v6 set. Alternatives:
`mpc-crowd` (closed-loop rollouts + prediction-uncertainty inflation for dense
pedestrian traffic), `stateful` and `waypoint` (experimental detour planners).
Baseline runs always use the shared law, so every frozen measurement is unchanged.

### Deterministic obstacle-velocity estimator (sensor infrastructure, not policy)
- `SensorSystem` keeps, per obstacle ID, a bounded deque of the last 16 DELIVERED
  world-frame position estimates (`observed robot pose + relative vector`, noisy/stale
  as delivered — never ground truth).
- Velocity = least-squares slope over the window; `confident` only with >= 3 samples
  spanning >= 2 ticks. Otherwise velocity is 0/unknown and the policy treats the
  obstacle as static (conservative fallback).
- `SensorObservation.tracks[]` carries `{id, vx_mps, vy_mps, samples, confident}`.
- Avoidance steering activates ONLY when `obstacle_prediction_horizon_s > 0` and the
  track is confident; predicted robot-frame position `horizon` seconds ahead pushes
  the desired heading laterally inside the influence radius
  (`safe + reaction + 0.5*speed*horizon + obstacle radius`, fixed blend gain 2.0).
- With horizon `0.0` the block is skipped entirely: baseline behavior is
  bit-identical to the brake-only law (verified: reference run repeats
  tick-for-tick).
- Occlusion: an obstacle hidden behind a closer one is not observed at all.
- Sensor models (`RW_SENSOR_MODEL`): `legacy` (exact delayed geometry, default;
  all frozen results use this) or `beam` (24-ray LiDAR-like casting — obstacles
  are only seen when a ray strikes them, with quantized bearing).

## 4. Telemetry Frame (`TelemetryFrame`)
Recorded per simulation tick:
- `schema_version`: Literal `"1.0"`
- `tick`: integer
- `sim_time_s`: float
- `robot`: `Pose2D`
- `obstacles`: List of `[{id, x_m, y_m, radius_m}]`
- `sensor`: `{sample_tick, delivered_tick, age_s, valid, observations}`
- `command`: `{linear_mps, angular_radps}`
- `clearance_m`: float
- `events`: List of `[{event_id, type, tick, details}]`

### Scenario from grid text or camera photo
- `POST /api/maps/scenario` turns occupancy-grid text into a validated
  `ScenarioSpec` (connected clusters → circle obstacles, ≤8, clamp warnings).
- `POST /api/scenarios/from-image/detect` runs real SAM 3.1 segmentation on an
  uploaded still (PNG/JPEG/WebP, ≤5 MB, 16–2048 px; animated/EXIF-rotated rejected)
  and stores only measured boxes + a source SHA-256 — never the photo.
- `POST /api/scenarios/from-image/scenario` projects selected boxes onto the
  user-calibrated floor rectangle (explicit scale + overhead-view confirmation required,
  start/goal placed on the image) into a runnable `ScenarioSpec`
  (`RW-IMG-<hash>`), with honest warnings: static circles only, no depth/perspective/
  hidden-obstacle/velocity recovery. Oversized/overlapping/invalid selections are
  rejected, never silently shrunk. `GET /api/scenarios/from-image/saved` lists them.

## 5. API Endpoints (`/api` prefix; auth optional, see `docs/ENTERPRISE.md`)

| Method | Path | Request Body | Response Body |
|---|---|---|---|
| GET | `/api/health` | None | `{status, schema_version, db_status, worker_active, ai_mode, ai_provider, meta_model}` |
| GET | `/api/scenarios/reference` | None | List of ScenarioSpec (canonical `RW-REF-001`) |
| GET | `/api/scenarios/library` | None | 20 catalog entries: 10 `RW-LIB-*`, 5 `RW-ULTRA-*`, 5 `RW-CROWD-*` |
| POST | `/api/scenarios/generate` | `{objective?, constraints?}` | `{scenario: ScenarioSpec, provenance: AIProvenance}` |
| POST | `/api/runs` | `{scenario, policy, local_policy?}` + optional `Idempotency-Key` | `{job_id, run_id, status: "queued"}` (202 Accepted) |
| GET | `/api/jobs/{job_id}` | None | `{job_id, status, progress, error, result_id}` |
| POST | `/api/jobs/{job_id}/cancel` | None | `{job_id, status: "cancelled"}` |
| GET | `/api/runs/{run_id}` | None | `{run_id, scenario_hash, policy_hash, oracle_status, reason_codes, metrics}` |
| GET | `/api/runs/{run_id}/telemetry` | `?offset=0&limit=600` | `{frames, total, offset, next_offset}` |
| POST | `/api/failures/{run_id}/investigate` | `{}` | `{investigation_id, hypothesis, evidence, patch, provenance}`; `409` unless the run is FAIL |
| POST | `/api/fixes/verify` | `{baseline_run_id, candidate_policy}` | `{job_id, verification_id, status: "queued"}` |
| GET | `/api/verifications` | `?limit=` | Verification summaries, newest first |
| GET | `/api/verifications/{verification_id}` | None | `{verification_id, verdict, gates, baseline_run_id, candidate_policy}` |
| GET | `/api/verifications/{verification_id}/candidate-telemetry` | `?offset=&limit=` | Sealed candidate replay frames |
| GET | `/api/evidence/{verification_id}` | None | Manifest, report, hashes, integrity status |
| GET | `/api/evidence/{verification_id}/download` | None | Safe ZIP stream |
| GET / POST | `/api/robots` | `RobotProfileCreate` | Robot catalog (builtin + workspace user robots) |
| GET / PUT / DELETE | `/api/robots/{robot_id}` | `RobotProfileCreate` | Single robot; builtins are read-only (403) |
| POST | `/api/robots/{robot_id}/apply-to-scenario` | `ScenarioSpec` | Scenario with the robot's body/sensor fields applied |
| GET / POST | `/api/policy-profiles` | `PolicyProfileCreate` | Named 5-parameter presets (4 builtin + user) |
| GET / PUT / DELETE | `/api/policy-profiles/{profile_id}` | `PolicyProfileCreate` | Single profile; builtins are read-only (403) |
| GET | `/api/local-policies` | None | `{enabled, policies[]}` — user Python plugins in `app/policies/local/` |
| POST | `/api/batteries` | `{robot_id, scenario_ids?, policy, local_policy?}` + optional `Idempotency-Key` | `{job_id, battery_id}` (202); default battery = reference + 10 library scenarios |
| POST | `/api/batteries/fleet` | `{robot_ids[], scenario_ids?, policy}` | Per-robot battery jobs; incompatible robots skipped with reasons |
| GET | `/api/batteries` | `?limit=` | Report cards, newest first |
| GET | `/api/batteries/trend` | `?robot_id=&limit=` | Pass-rate history, oldest first |
| GET | `/api/batteries/compare?a=&b=` | None | Per-scenario improved/worsened/same + summary deltas |
| GET | `/api/batteries/{battery_id}` | None | Full report card (entries trace to `run_id`s) |
| GET | `/api/batteries/{battery_id}/report.md` | `?lang=tr\|en` | Markdown report card (generated, not sealed) |
| POST / GET / DELETE | `/api/batteries/schedules` | `{name, robot_id, policy, scenario_ids?, interval_minutes}` | Recurring batteries; worker enqueues due ones once |
| POST | `/api/imports/telemetry` | `{name, format: csv\|json, content, goal?}` (≤20 000 frames) | Judged `REAL_LOG` verdict via the same oracle rules |
| GET | `/api/imports` | `?limit=` | Import history |
| GET | `/api/imports/{import_id}` | None | Single import result |
| POST | `/api/maps/scenario` | `{name, grid_text, cell_size_m}` | Grid text → validated `ScenarioSpec` (≤8 circle obstacles) |
| POST | `/api/scenarios/from-image/detect` | `{image_data_url, concepts[]}` | Real SAM 3.1 detections (recorded in tests, live via key) |
| POST | `/api/scenarios/from-image/scenario` | `{detection_id, selected_ids[], width_m, height_m, start, goal, save}` | Previewed or saved runnable `ScenarioSpec` + warnings |
| GET | `/api/scenarios/from-image/saved` | None | Saved image scenarios, newest first |
| GET | `/api/metrics` | None | Workspace counts, last battery summary, job states |
| GET | `/api/prom` | None | Prometheus exposition (public, like health) |
| GET | `/api/audit?limit=` | None | Write audit trail (admin role) |
| POST / GET / DELETE | `/api/admin/api-keys` | `{label, role, workspace_id}` | DB-managed keys (hash-only, one-time plaintext, 422-guarded first key) |
| POST | `/api/admin/backup` | None | WAL-safe SQLite backup + SHA-256 |
| GET | `/api/admin/backups` | None | Backup file list |
| POST | `/api/admin/retention` | `{older_than_days, dry_run}` | Delete old tenant history (never sealed evidence) |
| POST | `/api/admin/restore` | `{file}` | Restore from backup (pre-restore safety copy + SHA-256) |
| GET | `/api/workspaces/export` | None | Full tenant-data JSON bundle (admin) |
| POST | `/api/workspaces/import` | `WorkspaceExport` | Restore into the caller's workspace (no history overwrite) |
