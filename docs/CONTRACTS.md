# RoboWitness Canonical Data Models & API Contracts

This document formalizes the canonical contracts and data models required by `ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md`.

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

### Shared navigation law (baseline and candidate run the SAME algorithm)
Proportional heading to goal + braking on delayed sensor distance + horizon-gated
lateral avoidance. Only the five numeric fields above may differ between runs.

### Deterministic obstacle-velocity estimator (sensor infrastructure, not policy)
- `SensorSystem` keeps, per obstacle ID, a bounded deque of the last 8 DELIVERED
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

## 5. API Endpoints

| Method | Path | Request Body | Response Body |
|---|---|---|---|
| GET | `/api/health` | None | `{status, schema_version, db_status, worker_active, ai_mode}` |
| GET | `/api/scenarios/reference` | None | List of ScenarioSpec |
| POST | `/api/scenarios/generate` | `{objective?, constraints?}` | `{scenario: ScenarioSpec, provenance: AIProvenance}` |
| POST | `/api/runs` | `{scenario: ScenarioSpec, policy: PolicyConfig}` | `{job_id, run_id, status: "queued"}` (202 Accepted) |
| GET | `/api/jobs/{job_id}` | None | `{job_id, status, progress, error, result_id}` |
| POST | `/api/jobs/{job_id}/cancel` | None | `{job_id, status: "cancelled"}` |
| GET | `/api/runs/{run_id}` | None | `{run_id, scenario_hash, policy_hash, oracle_status, reason_codes, metrics}` |
| GET | `/api/runs/{run_id}/telemetry` | `?offset=0&limit=600` | `{frames, total, offset, next_offset}` |
| POST | `/api/failures/{run_id}/investigate` | `{}` | `{investigation_id, hypothesis, evidence_window, patch_proposal, provenance}` |
| POST | `/api/fixes/verify` | `{baseline_run_id, candidate_policy}` | `{job_id, verification_id, status: "queued"}` |
| GET | `/api/verifications/{verification_id}` | None | `{verification_id, verdict, gates, baseline_run_id, candidate_policy}` |
| GET | `/api/evidence/{verification_id}` | None | Manifest, report, hashes, integrity status |
| GET | `/api/evidence/{verification_id}/download` | None | Safe ZIP stream |
