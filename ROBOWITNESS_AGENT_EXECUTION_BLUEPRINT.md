# RoboWitness — Agent-Executable Engineering Blueprint

**Version:** 2.0  
**Language:** English  
**Execution mode:** Autonomous, sequential implementation  
**Product stage:** Four-day, software-only hackathon MVP  
**Primary deliverable:** A locally runnable, end-to-end RoboWitness application, not a prototype slideshow.

> **Product promise:** RoboWitness does not merely discover simulated robotic failures. It produces reproducible technical evidence showing whether a proposed fix actually survives independent verification.

> **Core invariant:** **The AI proposes. The simulator executes. The independent oracle decides. The evidence explains.**

---

# 0. READ THIS FIRST — MANDATORY INSTRUCTIONS FOR THE CODING AGENT

## 0.1 Exact START behavior

**Trigger:** The human says `START`, `Start`, `başla`, `implement`, `begin`, `continue implementation`, or otherwise explicitly asks to begin work.

**On that trigger, immediately perform the following actions IN THE WORKSPACE, using available tools:**

1. Inspect the working directory and the existing repository files. Use the existing repository root if present; otherwise create the `robowitness/` project in the current workspace. Never create a second nested project by accident.
2. Read this entire blueprint, then read `AGENTS.md`, `README.md`, package manifests, lockfiles, and existing code when present. Respect higher-priority instructions and avoid destroying existing work.
3. Create or update `docs/IMPLEMENTATION_STATUS.md` with the phase checklist, current phase, evidence/commands, known issues, and next action. Preserve completed history.
4. **Begin writing real implementation code in Phase 01 immediately.** Do not respond with another architecture proposal, to-do-only document, or request for permission to start.
5. Finish each phase's functional checks and tests before moving on. Record exact commands and their actual results, then proceed automatically to the next phase.
6. Continue through Phases 01–12 in order within the available working session. If interrupted, resume at the earliest unverified acceptance gate; do not restart finished phases.
7. At the end, report what is implemented, which checks ran and passed/failed, where evidence lives, and any actual blockers. Never claim tests passed unless they were executed.

**No unnecessary clarification questions.** Resolve noncritical implementation details using the explicit defaults and decisions below. Ask the human only when a genuinely indispensable secret, authorization, or external account action is required. Lack of a Meta API key is **not** a blocker: complete the offline path and clearly mark live Meta integration unverified.

**No fake completion:** Writing placeholder functions, mocked HTTP success, fabricated metrics, hard-coded PASS verdicts, or pretty UI fed by fake telemetry does not satisfy any phase.

**Do not stop after scaffolding. Do not stop after the first demo.** Finish as many successive validated phases as the environment genuinely permits. Do not claim unattended execution after the working session ends.

## 0.2 Decision priority (highest first)

1. Security, human instructions, existing repository invariants, and preservation of user data.
2. A real, reproducible, independently checked simulation-to-evidence loop.
3. Correct, validated backend contracts and automated tests.
4. A working, truthful dashboard and easy local startup.
5. Live Meta AI connectivity when credentials and an accessible endpoint exist.
6. Cosmetic polish and optional extensions.

If time is constrained, **remove polish, never correctness gates**. Do not simplify by quietly disabling the oracle, discarding failures, reducing required holdout size while still claiming verification, or inventing successful runs.

## 0.3 Agent operating rules

- **Implement; do not only describe.** Every phase requires changes to actual source/tests/configuration.
- Work **serially**, following dependencies. Do not launch competing edits/builds to the same source files.
- Keep modules small, typed, deterministic, and testable. No unnecessary frameworks, plugin systems, cloud services, queues, agents, or microservices.
- Prefer project-local dependencies and reproducible lockfiles. Avoid arbitrary major upgrades to existing projects. If starting fresh, select currently compatible stable versions, pin them in lockfiles, and record installed versions; do not blindly invent package versions.
- Always execute the repository's tests/lint/type checks after relevant changes. Fix failures before continuing. A skipped test is not a passed test.
- Never change business-rule thresholds after seeing a candidate's results to make that candidate pass. Fix scenario mechanics or calibration transparently **before** freezing evaluation fixtures.
- Keep credentials only in environment variables. Never commit `.env`, tokens, screenshots of secrets, real API responses containing secrets, or generated artifacts.
- Use only whitelisted, schema-validated AI output. **Never execute code returned by a model.**
- No CI, deployment, pushing to remote, or external messaging is needed for this MVP unless explicitly requested.
- No real robots, ROS 2, physical sensors, cameras, motor drivers, external hardware, or claims of physical-world safety.
- Prefer a working local-first application on Windows/WSL, macOS, or Linux over optimizing for a hosted production environment.
- Make honest scope distinctions: `OFFLINE_REFERENCE`, `LIVE_META`, and `UNAVAILABLE` are separate, visible provenance states.
- If a check fails, diagnose and repair the actual cause, rerun that check, and record the result. If truly blocked, record the exact blocker and continue only with technically independent work.

## 0.4 Required progress document format

Create `docs/IMPLEMENTATION_STATUS.md` and maintain a compact table:

| Phase | State (`NOT_STARTED`/`IN_PROGRESS`/`PASS`/`BLOCKED`) | Deliverables | Exact verification command | Actual result |
|---|---|---|---|---|

Below the table include `Current phase`, `Last verified checkpoint`, `Open issues`, `Decisions/deviations`, and `Next executable action`. Record source changes and test results; do not record forecasts as facts.

## 0.5 Definition of "ready to proceed"

For any phase: all stated files/features exist; intended behavior is real; its acceptance tests actually pass; commands and output are recorded; the next phase has a working dependency. If a test cannot run due to environmental constraints, mark the phase `BLOCKED`, explain why, and do not count it as completed.

---

# 1. Product boundaries and reference demo

## 1.1 The one supported MVP robot and world

- Robot: **one differential-drive-style, wheeled mobile robot** represented as a planar circular body.
- World: **one bounded, top-down virtual warehouse** with walls, goal, and circular obstacles.
- Primary challenge: **a moving obstacle plus delayed, optionally noisy virtual distance/relative-position observations**.
- Runtime: **PyBullet in `DIRECT` mode**, with a fixed simulation tick. The controller uses differential-drive kinematics and PyBullet geometries/contact checks; do **not** claim high-fidelity wheel/actuator dynamics if they were not implemented.
- UI: replay recorded poses and events on an HTML Canvas. Canvas is a viewer, **not** an independent simulation engine.
- End-to-end path: `Scenario → Baseline Run → Failure Investigation → Candidate Fix → Paired Run → Holdout + Regression → Verdict → Evidence`.

## 1.2 Required live demonstration

The local demo must support all three paths:

**Path A — Failure detected:** Start the predefined reference scenario with a delayed sensor; the unmodified baseline **actually** violates an oracle rule under measured simulation telemetry. It must be reproducible with its seed and frozen versions.

**Path B — Improvement accepted:** Run an allowed controller-parameter candidate; only label `VERIFIED_IN_SIMULATION` if the paired test, **all 20 frozen holdouts**, critical regressions, and evidence checks succeed. It is allowed that a particular candidate fails: tune a legitimate candidate *before freezing evaluation fixtures* rather than changing verdicts or pretending it succeeded.

**Path C — AI suggestion rejected:** Apply an over-conservative or otherwise faulty parameter proposal; demonstrate that even if collision avoidance improves, a real timeout, stuck condition, holdout failure, or regression causes `REJECTED` and displays its reason.

If Path B cannot meet its checks in the actual implemented physics model, show a truthful `REJECTED` or `INCONCLUSIVE` verdict. Never manufacture a positive demonstration.

## 1.3 Explicitly out of scope

Production distribution; real-world safety certification; ROS 2; SLAM; camera systems; real lidar; articulated arms; humanoids; multi-robot planning; cloud services; large language model fine-tuning; self-modifying code; fully realistic wheel friction; Kubernetes; PostgreSQL; Redis; Celery; native mobile apps; unrestricted user-defined Python.

---

# 2. Frozen MVP technical choices

| Layer | Choice | Mandatory implementation note |
|---|---|---|
| Repository | Monorepo | Single top-level README, scripts, and status document |
| API | Python 3.11+ with FastAPI, Pydantic v2 | JSON contracts and OpenAPI |
| Physics | PyBullet `DIRECT` | Separate client per simulation; fixed 1/60-second tick |
| Control | Pure Python, typed | Controller sees only `SensorObservation`, never world ground truth |
| Oracle | Pure Python deterministic geometry/metrics | Separate from policy and AI, unit-tested independently |
| Jobs | SQLite + one local worker process | Persistent state, single owner, atomic claim, polling |
| Storage | SQLite + local filesystem | Atomic evidence writes and file integrity hashes |
| AI | Configurable Meta model endpoint adapter | No invented model IDs/endpoints; bounded calls, offline fallback |
| Web | Next.js App Router + React + TypeScript | Canvas replay, REST polling, schema-based responses |
| UI state | Lightweight React state | No Redux/global-state framework required |
| Testing | pytest + backend HTTP tests + frontend type/lint + browser smoke | Verify behaviors, not just module imports |
| Local launch | Documented backend/web/worker commands | Docker Compose optional, not a prerequisite |

**Dependency rule:** When starting from an existing repo, inspect the actual versions and keep compatible working packages. When fresh, use supported stable releases from real registries, generate committed lockfiles, and record exact environment details. Do not rely on hypothetical API fields or non-existent library functions.

**Canonical naming:** snake_case in Python and on-the-wire JSON. TypeScript types mirror OpenAPI-generated types or carefully maintained typed interfaces. Use UTC ISO 8601 timestamps with `Z` for event creation times; `sim_time_s` is a separate simulated-time float. Distances are meters, angles radians, velocities m/s, durations seconds unless suffixed otherwise.

---

# 3. Prescribed repository structure

Create these paths incrementally in their responsible phases. Do not create empty placeholders to pretend completion.

```text
robowitness/
├── README.md
├── AGENTS.md                         # Instruct other coding agents to follow this blueprint
├── ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md
├── .gitignore
├── .env.example
├── Makefile                          # Or cross-platform scripts if Make unavailable
├── docs/
│   ├── IMPLEMENTATION_STATUS.md
│   ├── CONTRACTS.md
│   ├── EVIDENCE_FORMAT.md
│   └── DEMO_GUIDE.md
├── backend/
│   ├── pyproject.toml
│   ├── requirements.lock             # Or equivalent reproducible lock strategy
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── schemas/
│   │   │   ├── scenario.py
│   │   │   ├── policy.py
│   │   │   ├── jobs.py
│   │   │   ├── telemetry.py
│   │   │   ├── verification.py
│   │   │   └── ai.py
│   │   ├── simulation/
│   │   │   ├── world.py
│   │   │   ├── robot.py
│   │   │   ├── obstacles.py
│   │   │   ├── sensors.py
│   │   │   └── runner.py
│   │   ├── policies/
│   │   │   ├── baseline.py
│   │   │   └── configurable.py
│   │   ├── verification/
│   │   │   ├── oracle.py
│   │   │   ├── metrics.py
│   │   │   ├── paired.py
│   │   │   ├── holdout.py
│   │   │   └── regression.py
│   │   ├── ai/
│   │   │   ├── adapter.py
│   │   │   ├── prompts.py
│   │   │   ├── scenario_generator.py
│   │   │   └── investigator.py
│   │   ├── evidence/
│   │   │   ├── recorder.py
│   │   │   ├── integrity.py
│   │   │   └── reporter.py
│   │   ├── jobs/
│   │   │   ├── repository.py
│   │   │   ├── worker.py
│   │   │   └── service.py
│   │   ├── api/
│   │   │   ├── routes_health.py
│   │   │   ├── routes_scenarios.py
│   │   │   ├── routes_runs.py
│   │   │   ├── routes_failures.py
│   │   │   ├── routes_verifications.py
│   │   │   └── routes_evidence.py
│   │   └── db.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── apps/
│   └── web/
│       ├── package.json
│       ├── package-lock.json         # Or retained lockfile matching installed manager
│       ├── tsconfig.json
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── page.tsx
│       │   └── globals.css
│       ├── components/
│       │   ├── ScenarioPanel.tsx
│       │   ├── SimulationCanvas.tsx
│       │   ├── ReplayControls.tsx
│       │   ├── Timeline.tsx
│       │   ├── FixComparison.tsx
│       │   ├── VerificationDecision.tsx
│       │   └── EvidencePanel.tsx
│       ├── lib/
│       │   ├── api.ts
│       │   ├── types.ts
│       │   ├── playback.ts
│       │   └── geometry.ts
│       └── tests/
├── scenarios/
│   ├── reference/
│   │   └── moving_obstacle_latency.json
│   ├── regression/
│   │   ├── clear_corridor.json
│   │   ├── stationary_obstacle.json
│   │   └── goal_reachability.json
│   └── holdout/
│       └── manifest.json             # Exactly 20+ fixed unique scenario IDs/seeds
├── scripts/
│   ├── bootstrap.sh
│   ├── bootstrap.ps1
│   ├── smoke_test.py
│   ├── verify_evidence.py
│   └── run_offline_demo.py
└── artifacts/                       # Ignored from version control
    ├── runs/
    └── verifications/
```

Where the repo already has equivalent paths, reuse and document them rather than breaking functional code solely to match names.

---

# 4. Data model — canonical contracts before implementation

Implement the following with Pydantic v2 `extra="forbid"` for untrusted request objects, finite-number checks, explicit range validation, and serialization tests. Do not use free-form `dict` for domain objects except bounded metadata.

## 4.1 Shared geometry

- `Point2D`: `x_m: float`, `y_m: float`.
- `Pose2D`: `x_m: float`, `y_m: float`, `yaw_rad: float`.
- `Vector2D`: `x_mps: float`, `y_mps: float`.
- All coordinates finite; within the world after radius clearance; yaw finite and normalized to `[-pi, pi)` in serialization.
- Warehouse world boundaries: `[0, width_m] × [0, height_m]`; this describes the *inside* of the warehouse.
- Obstacles and robot have actual circular collision radii. Surface clearance = center distance minus the sum of radii. A contact/overlap is clearance `<= 0` (within documented numerical tolerance).
- Geometry calculations for oracle and simulation must be maintained in **separate modules**; policy cannot import either ground-truth implementation.

## 4.2 `ScenarioSpec` (fully required normalized form)

```json
{
  "schema_version": "1.0",
  "id": "RW-REF-001",
  "kind": "dynamic_obstacle",
  "seed": 1842,
  "world": {
    "type": "warehouse",
    "width_m": 12.0,
    "height_m": 8.0,
    "duration_limit_s": 30.0,
    "fixed_timestep_s": 0.016666666666666666
  },
  "robot": {
    "kind": "differential_drive",
    "start": {"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
    "goal": {"x_m": 11.0, "y_m": 4.0},
    "goal_radius_m": 0.35,
    "body_radius_m": 0.25,
    "wheel_base_m": 0.42,
    "wheel_radius_m": 0.09,
    "sensor_range_m": 4.0,
    "sensor_latency_ms": 450,
    "sensor_noise_std_m": 0.0
  },
  "obstacles": [
    {
      "id": "O1",
      "shape": "circle",
      "radius_m": 0.35,
      "motion": "ping_pong",
      "start": {"x_m": 6.0, "y_m": 1.0},
      "end": {"x_m": 6.0, "y_m": 7.0},
      "speed_mps": 0.45
    }
  ],
  "oracle": {
    "collision_free": true,
    "min_clearance_m": 0.25,
    "must_reach_goal": true,
    "max_duration_s": 30.0,
    "max_stuck_duration_s": 3.0
  }
}
```

**Important:** These coordinates and speeds form a **starting fixture**, not a pre-certified result. The agent must run the actual engine and transparently calibrate a reproducible failure and a viable candidate *before* freezing its acceptance fixtures. Do not hard-code the expected verdict into scenario data.

Allowed MVP constraints:

| Field | Allowed values / bounds |
|---|---|
| `schema_version` | Literal `1.0` |
| `kind` | `static_obstacle` or `dynamic_obstacle` |
| `seed` | Integer `0..2^32-1` |
| world size | width `6..20` m; height `4..15` m |
| `fixed_timestep_s` | Exact canonical `1/60`; use integer tick counts internally to avoid floating drift |
| `duration_limit_s` | `5..60` s, max 3600 steps |
| robot body radius | `0.15..0.40` m |
| start/goal | Within bounds with radius margin, physically valid and not initially overlapping obstacles |
| goal radius | `0.20..0.60` m |
| sensor latency | `0..1000` ms, translated into an integer delivery tick with a documented rounding policy |
| noise std | `0..0.2` m; use deterministic seeded RNG |
| obstacle count | `0..8`, unique IDs |
| obstacle radius | `0.15..0.80` m |
| obstacle motion | `static` or `ping_pong`; static uses identical start/end and zero speed |
| moving obstacle speed | `0.0..1.5` m/s, positive for moving case |
| oracle min clearance | `0.0..1.0` m, frozen at start of each test |
| max duration | Must not exceed world duration limit |

Additional validators: movement segment must stay within warehouse bounds with radius margin; goal reachable geometrically in a static world when feasible; no overlapping initial bodies; no duplicate IDs; no NaN/Infinity; input JSON size <= 64 KB. Reject rather than silently clamping out-of-bounds inputs. Freeze normalized scenario JSON, including oracle thresholds, **before simulation**.

**Fixture rule:** Source fixtures and generated scenarios must use the same model and parser; never special-case `RW-REF-001` inside the simulator, oracle, or UI.

## 4.3 `PolicyConfig` — only AI-adjustable fields

```json
{
  "schema_version": "1.0",
  "id": "baseline-v1",
  "max_speed_mps": 0.75,
  "safe_distance_m": 0.30,
  "reaction_margin_m": 0.05,
  "brake_gain": 1.5,
  "obstacle_prediction_horizon_s": 0.0
}
```

Constraints: `max_speed_mps: 0.05..1.2`, `safe_distance_m: 0.20..2.0`, `reaction_margin_m: 0..1.0`, `brake_gain: 0.1..10`, `obstacle_prediction_horizon_s: 0..2.0`. Version and ID are assigned by trusted application logic, **not** model-authored strings. The AI can propose a **partial patch limited to these five numeric keys**. Every proposal is merged, validated, recorded, and applied only to a newly instantiated controller.

Implement a simple deterministic navigation law: proportional heading adjustment toward the goal; motion safety/braking based only on **time-delayed sensor-relative positions**; bounded wheel-derived forward/angular speeds. Controller must not access `ScenarioSpec.obstacles`' true positions, collision contacts, future true positions, the oracle, or global simulator state. An implementation may use deterministic obstacle-velocity estimates derived solely from previously delivered sensor observations to support the prediction horizon; document the estimator and handle missing history conservatively.

Define `ControllerInput` / `SensorObservation` as an immutable, typed value with timestamp, observed robot pose/heading as needed for dead reckoning, range/bearing or relative-obstacle measurements, observation age, goal-relative direction, and validity flags. Sensor observations at startup may be `NOT_READY`: controller behavior must be defined and tested. Define `ControlCommand` as `(linear_mps, angular_radps)` with finite clamped values. The same controller algorithm must be used for baseline and candidate; **only** allowed parameters may differ.

## 4.4 Telemetry/event schema

One `TelemetryFrame` per integer simulation tick, or a documented lossless raw stream plus an optional decimated UI view. Minimum fields:

```json
{
  "schema_version": "1.0",
  "tick": 120,
  "sim_time_s": 2.0,
  "robot": {"x_m": 2.3, "y_m": 4.0, "yaw_rad": 0.0},
  "obstacles": [{"id": "O1", "x_m": 6.0, "y_m": 1.9, "radius_m": 0.35}],
  "sensor": {"sample_tick": 93, "delivered_tick": 120, "age_s": 0.45, "valid": true, "observations": []},
  "command": {"linear_mps": 0.75, "angular_radps": 0.0},
  "clearance_m": 3.1,
  "events": []
}
```

**Illustrative numbers above are schema examples only, not observed values.** Actual telemetry must come solely from the run. Keep raw truth in recorder/oracle data, never in the controller observation. Capture wall collision, body contact, sensor availability, stuck, goal arrival, and timeout events with `event_id`, `type`, `tick`, and relevant object IDs. Define event ordering deterministically. For a contact and an oracle-geometry overlap in the same tick, produce explicit evidence without double-counting one collision episode.

A run result includes: `run_id`, `scenario_id`, `scenario_hash`, `policy_hash`, `job_status`, `oracle_status`, `reason_codes[]`, `metrics`, `artifact_path`, `created_at`, `started_at`, `finished_at`. `run_id` must be unique, opaque, and filename-safe. Use integer ticks for temporal ordering.

## 4.5 Verdicts, roles, and rule precedence

**Job lifecycle is different from scientific outcome.**

- Job: `queued → running → completed | failed | cancelled`.
- Run oracle: `PASS | FAIL | INCONCLUSIVE`.
- Verification: `VERIFIED_IN_SIMULATION | REJECTED | INCONCLUSIVE`.
- AI provenance: `LIVE_META | OFFLINE_REFERENCE | UNAVAILABLE`.

Rules:

1. Invalid/missing telemetry, invalid scenario, interrupted run, worker crash, integrity failure, or missing required tests => `INCONCLUSIVE`, **never PASS**.
2. For a complete valid run, a binding requirement violation => `FAIL`, with machine-readable `reason_codes`.
3. Only a complete valid run without binding violations => `PASS`.
4. A verification is `VERIFIED_IN_SIMULATION` **only** if baseline failure was actually reproduced, the candidate's paired run passes, all 20 required holdouts are valid and passing for the candidate, all critical regressions pass, no required baseline-passing regression degrades, and evidence integrity verifies.
5. A completed valid verification with a violated safety/performance gate => `REJECTED` and explicit rejection reasons.
6. If any mandatory gate is unevaluable or evidence is incomplete => verification `INCONCLUSIVE`, with precedence over attempted certification. A definite failure may be recorded in gate details but do not silently treat missing evidence as a clean reject or acceptance.
7. AI narrative/metadata never overrides any decision; UI must display the oracle decision and AI explanation separately.

Reason-code examples: `COLLISION`, `MIN_CLEARANCE_VIOLATION`, `GOAL_NOT_REACHED`, `TIMEOUT`, `STUCK`, `REPRODUCTION_FAILED`, `PAIRED_TEST_FAILED`, `HOLDOUT_FAILURE`, `REGRESSION_FAILURE`, `MISSING_TELEMETRY`, `ARTIFACT_INTEGRITY_FAILURE`, `WORKER_TIMEOUT`, `JOB_CANCELLED`, `INVALID_SCENARIO`.

---

# 5. Simulation semantics — do not invent behavior later

## 5.1 One authoritative tick loop

The simulator owns a distinct PyBullet connection: `p.connect(p.DIRECT)` and **always** `p.disconnect(client_id)` in `finally`. Every PyBullet call must pass the correct `physicsClientId` where supported, so concurrent/previous sessions cannot contaminate a run. Use `p.setTimeStep(1.0/60.0)`, disabled real-time simulation, seeded RNG, and exact scenario snapshot.

Per tick, in this order:

1. Update deterministic obstacle locations from `tick`, path endpoints, speed, and ping-pong phase (not wall-clock time).
2. Obtain the previous sensor sample whose scheduled delivery tick is now due; compute and queue a current observation from the true world **for future delivery only**.
3. Build sanitized `ControllerInput` from the delayed observations and allowed navigation inputs.
4. Call the selected policy once and apply bounded forward/turn motion from differential-drive kinematics to robot's planar pose.
5. Update PyBullet collider transforms, call the relevant PyBullet collision/physics step, and collect contact evidence.
6. Record authoritative positions, sensor age, command, contacts, and independent geometric clearance.
7. Run oracle rule evaluation for this tick and emit structured events.
8. Stop at goal completion or the fixed maximum tick count, recording a terminal event. Unsafe collision may end the run early if consistent across baseline/candidate; **document** that termination policy in contracts.

Prefer reliable, documented PyBullet primitives to sophisticated physics shortcuts. A planar differential-drive kinematic update with PyBullet collision/contact detection is acceptable for the MVP **only when labeled as such**. Do not assert full rigid-body wheel dynamics, advanced dynamics, or perfect physical realism.

## 5.2 Sensor-delay model

- A sample captured at tick `k` cannot be visible to the controller before `k + ceil(latency_s / dt)`; use the same deterministic policy for all runs.
- Model bounded field of view/range if implemented; do not silently provide obstacle positions outside range.
- Preserve sampling timestamp and delivery timestamp; `age_s` must match them.
- Noise uses a per-run RNG seeded with the scenario seed; the paired run's environment **and sensor noise realization** should be the same for baseline and candidate, independent of controller RNG consumption. Use separate seeded streams for world, sensor, and policy.
- Controller sees only delivered observations, never raw truth. Oracle sees raw truth, never a policy's hidden reasoning.
- Test latency `0`, `450`, `1000` ms and first-tick/no-ready-observation behavior.

## 5.3 Clearance, collision, progress

- Independently compute circular footprint clearance against obstacles and wall boundaries. Clearance means **surface-to-surface gap**; robot-wall clearance is distance from the robot's outer radius to the nearest inside boundary.
- Track per-tick minimum clearance across robot/obstacles/walls, including samples between widely spaced UI frames (the default recorder captures every tick).
- A collision can be detected by PyBullet contact **or** verified geometric overlap; log which evidence fired. Use a consistent tolerance, e.g. `1e-4 m`, in collision comparisons, document it, and test at/around the boundary.
- Goal reached when the robot center is within `goal_radius_m` of goal center, while all safety requirements still hold. Reaching goal cannot erase a prior collision.
- Stuck detection: no meaningful progress toward goal for `max_stuck_duration_s` while the goal is not reached; use a small documented numerical tolerance and avoid classifying intentional brief braking as stuck. Stuck is a performance violation, not automatic evidence of physical collision.
- Timeout: no goal by deadline (`ceil(duration_limit_s / dt)` ticks), with elapsed simulated time recorded. Do not treat elapsed wall-clock time as task completion duration.

## 5.4 Reproducibility guarantees

Replaying the same scenario, policy, seed, source revision, dependency set, and platform should produce matching verdicts and metrics within documented numeric tolerance. Compare stable observable metrics with explicit tolerances; do **not** promise bit-for-bit identical JSON across OS/CPU/PyBullet versions. Always record deviations if observed.

---

# 6. Independent verification protocol

## 6.1 Gate 1: reproduce original failure

Run the baseline against the reference scenario. Require `oracle_status == FAIL` from recorded physical/geometry metrics and a clear failure reason. If baseline unexpectedly passes, fail this verification gate: investigate fixture calibration instead of silently treating a PASS as a reproduced failure.

## 6.2 Gate 2: paired comparison

Run baseline and candidate from identical **immutable** scenario specification, seed, initial world state, goal, obstacle trajectory, sensor noise, time step, oracle rules, and versioned engine. Only `PolicyConfig` differs. Compare collision count, min clearance, goal reached, simulated duration, stuck intervals, and violation list. Record `scenario_hash` equality and distinct policy hashes.

## 6.3 Gate 3: holdouts — mandatory for VERIFIED label

- Prepare **at least 20 unique, valid** holdout scenarios with distinct IDs and seeds, derived from reasonable fixed perturbations of obstacle speeds/locations/latencies, with no initial overlaps.
- Store their ID, seed, scenario hash, generation recipe/version, and creation timestamp in `scenarios/holdout/manifest.json`.
- Freeze the manifest before submitting a candidate for final evaluation. Do not tune the evaluated candidate based on those holdout results and then describe a rerun on the same data as untouched holdout verification; create a newly versioned set if needed and disclose the iteration.
- At validation, confirm all 20 IDs are unique, all specs valid, all intended cases executed, no duplicate run counted, and candidate `PASS` on each mandatory case.
- Display `passed/total`, exact denominator, individual results, and provenance; `19/20` means **not verified**. A lesser test count may be used in development, but must yield `INCONCLUSIVE`, not `VERIFIED_IN_SIMULATION`.

## 6.4 Gate 4: regression

Maintain at least three frozen critical cases (clear corridor, static obstacle, goal reachability). For each case baseline and candidate are evaluated with unchanged scenario/oracle rules. A baseline-passing critical case becoming FAIL or INCONCLUSIVE under the candidate invalidates verification. Candidate must satisfy all critical regression requirements. Do not ignore time/safety regressions because the reference collision was fixed.

## 6.5 Gate 5: evidence integrity and verdict sealing

Before a verification can receive the successful label, build a complete evidence package with canonical filenames, required metadata, hashes, and a passing independent integrity check. Hash failures, missing member files, absent environment version, omitted holdout cases, or incomplete runs cause `INCONCLUSIVE`.

**Prevent circular certification:** Evaluate measured gates 1–4 into a **provisional** result, then write the full verification files and provisional report, then check that all required files and references exist. Seal the **final** verdict into the report and manifest, regenerate `hashes.json` over their final bytes, and independently re-verify the sealed package **before** publishing `VERIFIED_IN_SIMULATION`. Do not publish a successful final verdict based on unsealed or mutable files. If sealing/integrity fails, publish `INCONCLUSIVE` and the integrity reason in the database; keep the incomplete package clearly labeled and do not serve it as certified evidence. The checksum file never hashes itself.

## 6.6 Rejection demonstration

Include an optional offline-reference `over_cautious` proposal that sets an intentionally very low but still schema-valid max speed. Run it through the **same real gates**. It should fail goal time/stuck where physically appropriate, but the rejection must be computed by measured outcomes—not manually selected based on preset name. If that candidate unexpectedly passes, show what actually happened and choose a different valid faulty candidate using genuine measured behavior.

---

# 7. Meta AI integration — realistic, optional, strictly separated

## 7.1 Configuration

`.env.example` must include (with blank/example values, **never actual secrets**):

```dotenv
RW_META_API_KEY=
RW_META_BASE_URL=
RW_META_MODEL=
RW_AI_MODE=offline
RW_AI_TIMEOUT_SECONDS=20
RW_AI_MAX_RETRIES=2
RW_AI_MAX_INPUT_CHARS=16000
RW_AI_MAX_OUTPUT_TOKENS=1000
RW_AI_MAX_CALLS_PER_WORKFLOW=3
RW_AI_MAX_ESTIMATED_COST_USD=1.00
RW_DB_PATH=./artifacts/robowitness.sqlite3
RW_ARTIFACTS_DIR=./artifacts
RW_CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_RW_API_URL=http://localhost:8000
```

Use an actual documented hackathon-available Meta inference endpoint. **Do not guess that Meta hosts an OpenAI-compatible API at any particular URL.** If the provider is not available, implement a clean `ModelAdapter` interface with `MetaAdapter` for a validated provider integration and `OfflineReferenceAdapter` for stored local examples. Document provider-specific transport/response parsing and test with redacted fixtures. Do not mark `LIVE_META` until a genuine authenticated response has been received and validated.

## 7.2 AI responsibilities

1. Generate a `ScenarioSpec` constrained by the server's schema.
2. Explain observed failure(s) in terms of timestamps, measurements, and **testable hypotheses**.
3. Propose a patch containing only the five allowed numeric `PolicyConfig` fields, with an explanation.

AI must **never** author Python code to run, change oracle thresholds, edit the holdout set during evaluation, fabricate events, or declare a fix verified.

## 7.3 Structured, bounded handling

- Build short, JSON-only prompts with a precise expected schema and only minimized, bounded evidence snippets.
- Limit input/output sizes, provider timeouts, retries, and total calls; use exponential backoff only for transient errors, not validation failures endlessly.
- Validate model responses with Pydantic. Permit at most one controlled regenerate-on-invalid-JSON attempt inside the overall bounded retry policy.
- On failures, produce an explicit `UNAVAILABLE` or `OFFLINE_REFERENCE` result and keep real simulation runnable.
- Cache validated responses by normalized prompt + model ID + relevant scenario/evidence hash, labeling cache hits accurately.
- Track number of AI calls, token counts if provided by the backend, and **estimated** cost if pricing is configured. Never claim actual spend without provider billing evidence. The original hackathon's **$150 credit ceiling** is budget context, not a guaranteed currently available balance.
- Untrusted scenario prompts and log text are treated strictly as data, not instructions. Sanitize rendering, prohibit filesystem/path instructions in provider outputs, and never leak secrets to the UI.

## 7.4 Offline operation is a first-class feature

Offline reference examples (one scenario, at least one investigation text, candidate suggestions) may be stored and labeled. Only sensor/world physics and oracle results produced by an actual local run count as execution evidence. UI must visibly state whether the explanation is live AI, offline reference material, or unavailable.

---

# 8. API contract — implement with real JSON and stable errors

Use `/api` prefix, validation-generated OpenAPI, and consistent status codes. No route shall return synthetic success objects. All new queued work returns a `job_id`; read endpoints expose eventual run/verification resources. Keep original named endpoints where practical.

| Method | Path | Request | Success response / behavior |
|---|---|---|---|
| GET | `/api/health` | None | Process health, schema_version, db status, worker heartbeat visibility, ai_mode |
| GET | `/api/scenarios/reference` | None | List normalized bundled scenarios |
| POST | `/api/scenarios/generate` | `{objective?, constraints?}` | Validated spec + AI provenance or clear provider failure/fallback |
| POST | `/api/runs` | `{scenario: ScenarioSpec, policy: PolicyConfig}` | `202`, `{job_id, run_id, status:"queued"}` |
| GET | `/api/jobs/{job_id}` | None | Status, progress, timestamps, error code, result IDs |
| POST | `/api/jobs/{job_id}/cancel` | None | Accepted cancellation intent and resulting status |
| GET | `/api/runs/{run_id}` | None | Run metadata, status, objective metrics, oracle result |
| GET | `/api/runs/{run_id}/telemetry` | `?offset=0&limit=600` | Typed frames, total, offset, next_offset or null |
| POST | `/api/failures/{run_id}/investigate` | `{}` | Investigation with grounded evidence links + AI provenance |
| POST | `/api/fixes/verify` | `{baseline_run_id, candidate_policy}` | `202`, `{job_id, verification_id, status:"queued"}` |
| GET | `/api/verifications/{verification_id}` | None | Gate progress/results, verdict, run IDs, failure reasons |
| GET | `/api/evidence/{verification_id}` | None | Manifest/report metadata, required files and integrity results |
| GET | `/api/evidence/{verification_id}/download` | None | Safe zip from known artifact root; no arbitrary paths |

**Error envelope:**

```json
{
  "error": {
    "code": "SCENARIO_VALIDATION_FAILED",
    "message": "Scenario contains invalid geometry",
    "details": [{"field": "robot.start", "reason": "out_of_bounds"}],
    "request_id": "opaque-id"
  }
}
```

- `400` malformed domain semantics; `404` unknown ID; `409` invalid transition; `413` oversized body; `422` input-schema validation; `429` AI rate/budget limit; `500` unexpected internal error; `503` external AI unavailable when no fallback requested.
- Errors include no sensitive paths, tokens, stack traces, or provider response secrets. Server-side logs may contain redacted stack traces.
- Configure CORS only for known local frontend origin(s); never unrestricted wildcard CORS with credentials.
- Limit telemetry pagination, file-download size, and payload sizes. No untrusted file paths in API payloads.
- Web client must handle queued, running, completed, failed, cancelled, inconclusive, timeouts, empty telemetry, and provider-offline states.
- Keep the route and model contracts documented with actual request/response examples from tests, not invented output.

---

# 9. Durable jobs and storage semantics

## 9.1 Minimal SQLite schema

Implement migrations or idempotent schema initialization for:

- `jobs(job_id PK, kind, status, payload_json, result_id, attempts, created_at, started_at, finished_at, lease_owner, lease_until, error_code, progress_json)`.
- `runs(run_id PK, job_id FK, scenario_hash, policy_hash, oracle_status, reason_codes_json, metrics_json, artifact_dir, created_at, completed_at)`.
- `verifications(verification_id PK, job_id FK, baseline_run_id, candidate_policy_json, verdict, gates_json, artifact_dir, created_at, completed_at)`.
- Optional `ai_requests` for bounded usage/provenance. Avoid storing raw credentials or unredacted sensitive prompts.

Every payload versioned; DB path configurable; foreign keys enabled; use short transactions; WAL where supported; never hold a DB transaction across a full simulation. Provide helpful migration failure messages.

## 9.2 Worker behavior

- Run exactly one named worker process for MVP, separate from the API process. Claim queued jobs atomically inside a transaction (`BEGIN IMMEDIATE` or equivalent); verify only one worker owns a job. If accidentally started twice, jobs must not duplicate.
- Job states are persistent through API/worker restart. Worker updates progress at meaningful boundaries (e.g. each verification gate and 5% simulation increments) and heartbeat/lease.
- Set a finite wall-clock timeout per run and an aggregate verification timeout. Cancel cooperatively between simulation ticks and between holdouts; close PyBullet connections and flush partial evidence.
- On restart, recover expired `running` jobs deterministically: either safely requeue an **idempotent** job with a bounded attempt counter, or mark `failed`/`INCONCLUSIVE` with an explicit recovery reason. No permanently stuck `running` rows.
- Write artifacts first to a job-scoped temporary directory, fsync/flush as appropriate, then atomically rename into the final directory when complete. Never expose half-written output as complete evidence.
- All write paths must resolve below the configured artifact root; block `..`, symlinks leaving root, and path traversal.
- API may serve read-only results while worker computes; do not run heavy PyBullet simulations in FastAPI request threads or rely on background tasks that disappear on API restart.

---

# 10. Evidence package specification

For each run use `artifacts/runs/<run_id>/`, for each verification `artifacts/verifications/<verification_id>/` with references to constituent run IDs.

**Required per-run files:**

```text
scenario.json
policy.json
manifest.json
telemetry.jsonl
metrics.json
events.jsonl
hashes.json
```

**Required per-verification files:**

```text
manifest.json
investigation.json
comparison.json
holdout_results.json
regression_results.json
report.md
hashes.json
```

Mandatory run manifest fields: schema version, ID, scenario/policy SHA-256, source revision or `unknown`, Python/PyBullet dependency versions, OS/platform, simulator type, timestep, seed, creation/completion times, AI provenance when present, and **actual** test status. Verification manifest additionally lists all gate IDs, run IDs, frozen holdout manifest hash, all 20 holdout outcomes, regression cases, candidate hash, oracle version, and verdict.

Hash the exact bytes of every completed required member except `hashes.json` itself; store a mapping of relative filename → lowercase SHA-256 in `hashes.json`. Do not hash a file that contains its own hash (no circular manifest/checksum dependency). The integrity checker independently recalculates every listed digest, rejects missing required files and extra references outside root, and returns a structured pass/fail. The report is generated **from persisted measured data**, not free-floating AI text.

The report must state:

- Test scope, software-only limitation, and no physical-world safety claim.
- Scenario/seed/engine/controller versions.
- Baseline failure evidence with tick, clearance/contact, and reason.
- Candidate parameter diff, paired before/after metrics, and run IDs.
- Holdout count, result for each case, regression details, gates, and exact verdict.
- Failures, uncertainties, inconclusive/unexecuted tests, and AI provenance.
- How to reproduce locally and verify SHA-256 integrity.

Create a safe ZIP download containing exactly the allowed package tree and no secrets or traversal. Add a script to verify a saved package **without running AI**. Make evidence generation idempotent: reruns generate new IDs but stable measurement content within tolerances.

---

# 11. Dashboard interaction contract

Build **one functional workflow page**, not a multi-page mockup. Visually polished enough for a demo, but all primary controls must call real endpoints and reflect real jobs.

## 11.1 Mandatory functional regions

1. **Scenario**: reference scenario selection, validated AI-generated scenario, editable allowed scenario fields or a clear read-only summary, seed, source/provenance.
2. **2D Simulation**: top-down warehouse, boundary/goal, robot orientation, obstacle paths/positions, robot path, collision marker, minimum-clearance indicator. Coordinates converted consistently from meters to Canvas pixels; never invent robot pose.
3. **Replay**: play, pause, reset, step, speed `0.5x/1x/2x`, scrub/timeline; interpolation only for visual display, not evidence. Clearly distinguish simulated seconds from playback seconds.
4. **Failure Analysis**: oracle reason codes and measured events; AI narrative in separate labeled section with provenance.
5. **Candidate Fix**: editable whitelisted parameters, AI/offline proposal provenance, actual baseline-candidate diff, Verify action.
6. **Verification**: pending/running gate progress, `VERIFIED_IN_SIMULATION`/`REJECTED`/`INCONCLUSIVE` verdict, explanations, 20-case holdout pass count and regression results.
7. **Evidence**: view report, manifest, file list, hashes/integrity status, download ZIP.

## 11.2 Exact user action sequence

`Choose Scenario` → `Run Baseline` → `Replay Failure` → `Investigate` → `Review/Edit Candidate` → `Verify Candidate` → `Compare Runs` → `Inspect Verdict` → `Download Evidence`.

Enforce dependencies in the UI: do not enable investigation without a completed failed baseline; do not verify without a valid baseline failure and a validated candidate; show meaningful errors rather than silent no-ops. Never pre-populate a fabricated verification outcome. Clearly label reference/demo fixtures vs live Meta output.

## 11.3 Resilience and accessibility

- Poll jobs with bounded interval (e.g. 0.75–1.5 s), stop after terminal state, clean up on navigation/unmount; no interval leaks.
- A browser refresh must recover run/verification state via saved IDs (URL query or safe local storage; no secrets).
- Show a worker-offline indicator if heartbeat is stale and a model-unavailable label if Meta configuration is missing.
- Responsive on laptop screens; readable labels, keyboard-operable buttons, and status text not conveyed by color alone.
- Use loading, empty, error, inconclusive, success, and failure states for every async component.
- A demo screenshot is not proof: the UI's metrics and events must trace to actual response IDs and recorded artifacts.

---

# 12. Ordered implementation phases — FOLLOW THESE EXACTLY

**Run phases serially.** The `Exit gate` of one phase is a prerequisite of the next. A day boundary is planning guidance, **not** permission to skip tests. The status file must reflect actual work and any deviations.

## Day 1 — Real deterministic simulation core

### PHASE 01 — Repository, environment, contracts (FIRST EDIT)

**Create/modify:** `README.md`, `AGENTS.md`, this blueprint in project root, `.gitignore`, `.env.example`, `backend/pyproject.toml`, backend package, minimal frontend package, `docs/CONTRACTS.md`, `docs/IMPLEMENTATION_STATUS.md`.

**Actions in order:**

1. Inspect repo; preserve existing functionality and manifests.
2. Create project directories, environment instructions, local run commands; initialize Python environment and Node project only when needed.
3. Add Pydantic models for `Point2D`, `Pose2D`, `ScenarioSpec`, `PolicyConfig`, results/events with bounds and unknown-field rejection.
4. Store canonical reference scenario JSON, validate it from disk, and add serialization/hash utilities.
5. Generate FastAPI OpenAPI by importing app and validating schema; create `GET /api/health` with truthful state.
6. Add tests for positive parsing, unknown field, NaN/Infinity, wall overlap, duplicate obstacles, path constraints, version mismatch, and invalid policy values.

**Exit gate:** Dependency installation succeeds; Pydantic tests pass; reference fixture parses; `GET /api/health` succeeds through an HTTP test client; no placeholder output. Record exact commands.

### PHASE 02 — PyBullet world, deterministic sensor and controller

**Create/modify:** `simulation/world.py`, `robot.py`, `obstacles.py`, `sensors.py`, `runner.py`, `policies/baseline.py`, `policies/configurable.py`, first physical tests.

**Actions in order:**

1. Implement PyBullet `DIRECT` client lifecycle and actual geometry for robot, walls, and obstacles.
2. Implement fixed tick, ping-pong obstacle trajectory, planar differential-drive motion, and bounded sensor delivery queue.
3. Implement baseline controller with only allowed delayed observations; implement configurable policy by the same logic, parameterizing five fields.
4. Capture every-tick truth, delayed sensor, command and PyBullet contact events. Build deterministic CLI runner for one fixture.
5. Add unit tests for obstacle endpoints, tick ordering, first sensor observation, latency, noise seed isolation, speed limits, wall collision, and client cleanup on exceptions.

**Exit gate:** CLI creates real telemetry JSONL from actual PyBullet steps and repeats consistent metrics under same inputs. A deliberately colliding minimal scenario is caught by contact/geometry; safe empty corridor reaches goal. No AI or frontend required.

### PHASE 03 — Independent oracle and reference failure

**Create/modify:** `verification/oracle.py`, `metrics.py`, relevant runner integration, unit/integration tests, scenario fixture calibration.

**Actions in order:**

1. Implement independent surface clearance and wall gap calculations, goal, collision, stuck, timeout, and missing-data classification.
2. Freeze per-run oracle thresholds before stepping. Confirm failure still reported when goal reached after an earlier violation.
3. Run the reference fixture; inspect telemetry. If it does not genuinely fail, **calibrate documented scenario inputs or baseline policy using simulations**, then freeze a reproducible failing reference.
4. Run it at least three times with same seed/config; check reason codes and metrics within tolerances. Test a clean passing control fixture and corrupted/incomplete telemetry returning INCONCLUSIVE.

**Exit gate:** Actual `FAIL` and `PASS` and `INCONCLUSIVE` cases are all independently demonstrated by automated tests; reference `FAIL` repeats, with at least one measured tick and concrete rule. Log the frozen fixture hash.

### PHASE 04 — SQLite jobs, API, evidence for individual runs

**Create/modify:** `db.py`, `jobs/*`, `api/routes_health.py`, `api/routes_runs.py`, `api/routes_scenarios.py`, `evidence/recorder.py`, `evidence/integrity.py`, corresponding tests.

**Actions in order:**

1. Implement persistent job and run tables with schema init/migration and atomic claim.
2. Implement worker process and finite timeouts, cancellation, progress, restart handling, and worker heartbeat.
3. Make `POST /api/runs`, job polling, run reading, telemetry pagination call actual simulation via worker.
4. Persist canonical scenario/policy/manifest/telemetry/events/metrics and hashes atomically after real execution.
5. Add HTTP integration tests for create → worker process → completed job → run metrics → telemetry; unknown IDs, duplicate workers, failure states, and cancellation.

**Exit gate:** Fresh DB and artifact folder can execute a complete run via API+worker; data persists across API restart; integrity check passes; no test returns a manually fabricated verdict.

## Day 2 — AI adapter and working dashboard

### PHASE 05 — Schema-validated AI + offline references

**Create/modify:** `ai/*`, `schemas/ai.py`, `api/routes_scenarios.py`, `api/routes_failures.py`, `.env.example`, AI tests.

**Actions in order:**

1. Implement adapter protocol and offline reference implementation with explicit provenance.
2. Implement provider adapter behind validated, configurable transport; if endpoint/account cannot be verified, leave provider `UNAVAILABLE` rather than inventing requests.
3. Implement strict scenario generation, evidence-based investigation, and whitelisted partial policy patch suggestions.
4. Add bounded timeout/retry/budget/cost accounting, validation/rejection of malicious or malformed outputs, mock-provider integration tests, and provider-error fallback handling.
5. If valid credentials exist in environment, execute one genuine smoke call with a cheap request and record only sanitized evidence. If absent, mark live-provider test `NOT_RUN` and continue offline.

**Exit gate:** Offline scenario and investigation endpoints work without secrets; malicious/invalid AI responses do not alter thresholds or execute code; mock-provider tests pass. Live capability is labeled according to reality.

### PHASE 06 — Functional Canvas dashboard and replay

**Create/modify:** `apps/web/app/*`, `components/ScenarioPanel.tsx`, `SimulationCanvas.tsx`, `ReplayControls.tsx`, `Timeline.tsx`, `lib/*`, web tests.

**Actions in order:**

1. Build typed API client, validated responses, queued/running/error states, and bounded job polling.
2. Show reference or generated scenarios and allow baseline run submission.
3. Draw warehouse scale, goal, robot orientation and trajectories, moving obstacles, path history and markers from returned telemetry.
4. Provide timeline, scrubbing, stepping and replay speed controls; display actual oracle metrics and reason codes.
5. Test page state recovery, coordinate transformations, telemetry pagination, loading/errors, and basic keyboard use.

**Exit gate:** A person can start a **real** baseline from the browser, watch it complete, replay real recorded frames, and see the measured failure; frontend lint/typecheck/build pass.

## Day 3 — Investigation, real paired/holdout/regression verification

### PHASE 07 — Grounded investigation and candidate UI

**Create/modify:** `api/routes_failures.py`, `components/FixComparison.tsx` (initial), `components/FailureAnalysis.tsx` if needed, schemas/tests.

**Actions in order:**

1. Extract a bounded failure-evidence window by measured failure tick, including sensor age, commands, obstacle pose, and oracle events.
2. Generate a labeled AI hypothesis or offline example; store source and uncertainty.
3. Show hypothesis alongside objective evidence; expose the allowed policy parameters for edit/validation and show diff from baseline.
4. Reject any attempt to edit oracle thresholds, seed, frozen scenario or arbitrary source code through candidate patching.

**Exit gate:** Investigate action references an actual failed run; UI displays actual evidence and an appropriately labeled narrative; allowed numeric parameters can be submitted; forbidden edits are rejected in backend tests.

### PHASE 08 — Paired runs and verified baseline comparison

**Create/modify:** `verification/paired.py`, `schemas/verification.py`, `api/routes_verifications.py`, comparison UI, tests.

**Actions in order:**

1. Verify baseline `FAIL` is reproduced from immutable scenario before testing candidate.
2. Execute baseline and candidate in distinct simulation contexts with identical non-policy inputs and RNG streams.
3. Produce full before/after metrics, precise reason codes, scenario/seed equality evidence, and policy diff.
4. Store paired results; build initial verification job that reports gate progress and never prematurely certifies candidate.

**Exit gate:** Backend asserts equal paired scenario hashes and independent policy hashes; same-policy repeat is stable; good and bad candidate results arise from actual runs; partial workflow stays INCONCLUSIVE before all mandatory gates.

### PHASE 09 — Frozen 20 holdouts, regressions, and evidence-gated verdict

**Create/modify:** `verification/holdout.py`, `regression.py`, freeze 20-case manifest and 3+ regression scenarios, verification API, tests.

**Actions in order:**

1. Build 20 valid unique holdouts; lint each fixture and ensure no overlap/out-of-bound conditions. Freeze manifest hash before final candidate evaluation.
2. Build and check regression suite; record baseline results for each.
3. Implement gate-driven verification worker: reproduce → paired → holdout 20 → regressions → provisional decision → complete minimum evidence package → final integrity check → sealed verdict. Write required verification manifest, comparison, investigation, results and basic `report.md` here; Phase 11 improves/report-exports them, not invents an evidence gate later. Execute cases with recorded outcomes; allow early cancellation/timeout but then return INCONCLUSIVE.
4. Create a candidate that measurably improves reference behavior and test it without compromising a fixed holdout; reject invalid candidates or incomplete gate coverage.
5. Add negative tests: 19/20 cannot verify, one holdout failed causes REJECTED, previously passed regression failed causes REJECTED, missing telemetry causes INCONCLUSIVE, mismatched scenario hashes causes INCONCLUSIVE.

**Exit gate:** Live worker computes measured gate verdicts and exact totals, cannot assign VERIFIED before complete sealed evidence, and tests prove honest positive/negative/inconclusive handling. If no candidate passes all genuine gates, mark Path B unmet and report clearly; do not falsify it.

### PHASE 10 — Verification UI, comparison replay, explicit rejection

**Create/modify:** `components/FixComparison.tsx`, `VerificationDecision.tsx`, replay UI, integration tests.

**Actions in order:**

1. Wire Verify button to real queued job and show progress through each named gate.
2. Render side-by-side or toggled synchronized baseline/candidate replay from real distinct run IDs.
3. Display objective metric differences, holdout denominator, every failed case ID, regression details, and definitive reason codes.
4. Add demonstration candidate for rejection **without any hardcoded outcome**; show verdict measured by engine.

**Exit gate:** Browser can demonstrate failure, candidate verification, real gate details, and a real REJECTED decision from valid but ineffective fix. All UI checks pass.

## Day 4 — Audit-grade evidence, stability and demo

### PHASE 11 — Full evidence, download, independent reproduction

**Create/modify:** `evidence/reporter.py`, `api/routes_evidence.py`, `docs/EVIDENCE_FORMAT.md`, `scripts/verify_evidence.py`, `scripts/run_offline_demo.py`, tests.

**Actions in order:**

1. Audit and enrich the minimum already sealed verification manifest, investigation, comparison, holdout, regression and human-readable report from persisted facts; re-seal and verify whenever final bytes change.
2. Hash all required package members; independently verify digests and completeness; expose safe ZIP download.
3. Add a programmatic reproduction script for frozen seed/policy that compares results within documented tolerance and flags drift.
4. Create tampering tests (modified metric, missing file, changed seed, wrong hash) and ensure integrity failure cannot yield verified verdict.

**Exit gate:** A downloaded package is independently checkable offline; tampering is detected; report exactly matches recorded run IDs and results; one end-to-end evidence generation test passes.

### PHASE 12 — Fresh install, hardening and final demonstrator (DONE)

**Create/modify:** `README.md`, `docs/DEMO_GUIDE.md`, shell/PowerShell bootstrap, final tests and status record.

**Actions in order:**

1. Perform backend formatter/linter/type checks, pytest unit/integration, frontend lint/typecheck/build, and fresh local start smoke. Fix regressions instead of ignoring them.
2. Verify Windows/WSL-safe paths and localhost configuration; do not require Docker/WSL integration if normal local processes work.
3. Run `scripts/run_offline_demo.py` against a clean DB/artifact path: failure, investigation, candidate verification, rejected suggestion, complete evidence. Compare actual outputs with docs.
4. Verify browser flow with real browser automation if available; if unavailable, record as `NOT_RUN` and execute available HTTP/UI unit smoke checks instead.
5. Confirm startup instructions from a fresh checkout, missing-key fallback, no secret committed, CORS, cancellation, timeout, unexpected worker death, bad input, missing telemetry, artifact tampering, and corrupt JSON handling.
6. Print a short final status: completed features, exact passing commands, actual path to evidence, what could not be tested, real live Meta status, and any remaining risks.

**Exit gate / MVP DONE:** A new developer follows README and runs the entire local offline workflow with real PyBullet evidence; correct independent verdicts, full package integrity, and interactive replay. Any missing gate must be explicitly marked incomplete—not described as finished.

---

# 13. Minimal required test inventory

Use test names equivalent to the following, in addition to phase-specific tests. These are behavioral assertions, not mere code coverage targets.

| Suite | Required behavioral test |
|---|---|
| Schema | Reject NaN/Infinity, unknown fields, overlapping start, invalid obstacle path, out-of-range controller patch |
| Physics | 1/60 tick timing, endpoint obstacle reversal, PyBullet client cleanup, wall/contact event |
| Sensor | Zero latency, 450ms latency rounding, startup no sample, same-seed noise repeat |
| Controller | Never accesses ground truth; outputs finite bounded commands; parameter patch changes behavior |
| Oracle | Real contact FAIL; 0.25m clearance boundary; clean PASS; corrupted telemetry INCONCLUSIVE |
| Reproducibility | Same frozen seed/config produces stable reason codes and metrics within tolerance |
| Storage | Atomic job claim, restart recovery, API state persistence, path containment |
| API | Real create/poll/result/telemetry; 404/409/422 and worker-offline behavior |
| AI | Reject prompt injection, forbidden patch keys, non-JSON, oversized and provider timeout; offline mode works |
| Paired | Same scenario hash/seed, differing policy hashes, independent runs |
| Holdout | Exactly 20 distinct cases; 19/20 cannot be VERIFIED; one true failure => REJECTED |
| Regression | Candidate degrades baseline-passing critical run => REJECTED |
| Evidence | Missing member, byte tampering, wrong SHA, invalid run ref detected |
| UI | Real REST flow, load/error/recovery states, canvas transform and replay frame order |
| E2E | Fresh offline demo yields measured failure + rejection + package that hashes correctly |

**Expected test organization:** fast pure unit tests every phase; targeted integration tests after API/worker/AI additions; full end-to-end run before final. For each completed phase record actual command(s), exit codes and failing/passing counts. No tests should require live Meta credits in the default suite.

---

# 14. Launch, reproducibility and developer experience

The agent must provide **actual executable commands** in README, adjusted to the final generated project; examples below define intent, not permission to leave nonexistent scripts:

```bash
# Backend environment, from repository root
cd backend
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'

# Terminal A: FastAPI
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal B: single worker (same backend environment)
python -m app.jobs.worker

# Terminal C: frontend
cd ../apps/web
npm ci
npm run dev

# Tests (from correct working directories)
pytest -q
npm run lint
npm run typecheck
npm run build
```

If actual commands differ (e.g. `uv` or a different package manager), replace examples with tested commands and avoid contradictory instructions. Ensure a clean run can use `RW_AI_MODE=offline` and requires **no payment**, real API credentials, Docker Desktop, WSL integration, cloud account, or remote infrastructure. Document which local services/ports and worker are mandatory. Maintain `.env.example` and ensure `artifacts/`, `.env`, `.venv`, Next.js build output, and local caches are gitignored.

---

# 15. Failure-handling decision table

| Problem | Required behavior | Forbidden shortcut |
|---|---|---|
| Meta key absent | Offline path remains functional; label `OFFLINE_REFERENCE` | Pretend calls were made |
| Meta model returns unsafe/invalid output | Reject via schema; bounded retry; explicit fallback/error | Execute code or change rules |
| Reference fixture does not fail | Investigate and calibrate real mechanics; log deviation | Hard-code FAIL |
| Candidate does not pass | Explain measured reasons and reject/mark inconclusive | Hard-code VERIFIED |
| One holdout missing | `INCONCLUSIVE`, record 19/20 | Quietly accept 19/20 |
| Holdout valid but fails rule | `REJECTED` with case ID | Drop failing case |
| Worker stops mid-run | Safe cleanup, bounded recovery, incomplete result | Mark completed |
| Sensor data missing | Conservative controller behavior, explicit oracle coverage | Fill with invisible ground truth |
| Evidence hash wrong | Integrity fail and INCONCLUSIVE | Recalculate hashes after tampering to mask issue |
| Browser disconnects | Job continues independently; page can rehydrate | Lose only record of run |
| PyBullet/platform drifts numerically | Disclose environment/version and tolerance | Promise bitwise reproducibility |
| Stuck/goal timeout | Real failure reason and trace | Ignore performance for safety-only PASS |

---

# 16. Acceptance contract (all must be demonstrable)

A phase is not done because a file exists; the behavior must run. The final MVP is complete **only when** all requirements below are observed and recorded:

- [ ] One warehouse, one differential-drive-style robot, and PyBullet `DIRECT` simulations run locally.
- [ ] Scenario and policy inputs reject malformed, dangerous, out-of-range, or semantically impossible inputs.
- [ ] Delayed sensor observations are isolated from independently recorded ground truth.
- [ ] A frozen seeded reference failure is reproduced in **real simulated telemetry**.
- [ ] Objective `PASS`, `FAIL`, and `INCONCLUSIVE` verdicts have independent unit/integration tests.
- [ ] Offline reference scenario/analysis work without Meta API credentials.
- [ ] Live Meta scenario generation is tested with actual access **or plainly labeled unverified/unavailable**.
- [ ] Model proposals cannot execute code, change oracle thresholds, or change evaluation holdouts.
- [ ] Paired baseline/candidate runs use identical scenario, seed, and exogenous randomness.
- [ ] **At least 20** frozen distinct holdout cases are evaluated before any VERIFIED verdict.
- [ ] Critical regression cases can block a candidate.
- [ ] Valid, failed, and incomplete verification results yield honest distinct verdicts.
- [ ] The browser invokes actual backend jobs, plays real telemetry, and shows real comparisons.
- [ ] Evidence reports actual measured runs, provenance, versions, hashes, and limitations.
- [ ] Missing/tampered required evidence is detected by an independent verifier.
- [ ] Backend tests, frontend checks, and a full local offline run execute successfully.
- [ ] A fresh developer can install and run the application using the README.

If an item is not achieved, list it as incomplete with the exact technical reason. Never dilute the definition of complete to match partial progress.

---

# 17. After MVP — DO NOT IMPLEMENT BEFORE PHASE 12 PASSES

Optional future work: richer replay polish, synchronized comparison, improved robot dynamics, more scenario families, larger statistical verification, ROS integration, multiple robot types, PostgreSQL/Redis, cloud execution, authentication, CI integration, and video export. These must not delay or destabilize the four-day core path.

---

# 18. FINAL AGENT EXECUTION COMMAND

The human does **not** need to ask for any of the individual phases. When explicitly told `START` / `BAŞLA`, the coding agent shall:

```text
READ THIS BLUEPRINT COMPLETELY.
INSPECT THE ACTUAL REPOSITORY.
CREATE/UPDATE docs/IMPLEMENTATION_STATUS.md.
BEGIN PHASE 01 SOURCE CODE IMPLEMENTATION NOW.
RUN ITS ACCEPTANCE CHECKS AND RECORD ACTUAL RESULTS.
AUTOMATICALLY CONTINUE PHASE 02, THEN 03 ... THROUGH PHASE 12.
REPAIR FAILED CHECKS BEFORE CALLING A PHASE COMPLETE.
DO NOT ASK FOR PER-PHASE PERMISSION.
DO NOT CLAIM UNRUN TESTS, UNVERIFIED META ACCESS, OR FABRICATED VERDICTS.
IF INTERRUPTED, RESUME FROM THE EARLIEST UNVERIFIED GATE.
FINISH WITH HONEST IMPLEMENTATION STATUS AND REPRODUCIBLE EVIDENCE.
```

**RoboWitness succeeds when it can independently reject an apparently promising AI suggestion based on real, reproducible simulation evidence—not when its dashboard merely looks successful.**
