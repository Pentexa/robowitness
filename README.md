# RoboWitness

**Independent Verification Engine for AI Robotics Policy Fixes**

> **Core Invariant:** The AI proposes. The simulator executes. The independent oracle decides. The evidence explains.

---

## 1. Overview
RoboWitness is a locally runnable, software-only verification platform built to independently evaluate AI-generated robotics policy fixes. It enforces strict separation between:
1. **Controller Policies** — which only receive time-delayed, noisy sensor observations, never ground truth.
2. **Authoritative Physics** — simulated via PyBullet `DIRECT` mode at a deterministic 60Hz tick loop.
3. **Independent Oracle** — which decides objective PASS / FAIL / INCONCLUSIVE verdicts based on true geometric surface clearance, wall gaps, contacts, and timeouts.
4. **Independent Verification Protocol** — which gates candidate proposals across:
   - **Gate 1:** Baseline Failure Reproduction
   - **Gate 2:** Paired Comparison (identical seed, world state, obstacle trajectory)
   - **Gate 3:** 20 Frozen Holdout Scenarios
   - **Gate 4:** Critical Regression Suite
   - **Gate 5:** Cryptographic Evidence Sealing (`hashes.json`, SHA-256)

---

## 2. Repository Architecture

```text
robowitness/
├── README.md                         # Architecture and local run guide
├── AGENTS.md                         # Autonomous agent instructions
├── ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md
├── .gitignore
├── .env.example
├── Makefile                          # Development and testing targets
├── docs/
│   ├── IMPLEMENTATION_STATUS.md      # Live phase progress tracker
│   ├── CONTRACTS.md                  # Canonical schema specifications
│   ├── EVIDENCE_FORMAT.md            # Evidence package structure
│   └── DEMO_GUIDE.md                 # Three demonstration paths guide
├── backend/
│   ├── pyproject.toml
│   ├── requirements.lock
│   ├── app/
│   │   ├── config.py
│   │   ├── db.py                     # SQLite WAL persistence
│   │   ├── errors.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── schemas/                  # Pydantic v2 domain models
│   │   ├── simulation/               # PyBullet DIRECT 60Hz simulation
│   │   ├── policies/                 # Baseline & configurable policies
│   │   ├── verification/             # Oracle, paired, holdout, regression
│   │   ├── ai/                       # Meta AI adapter & offline reference
│   │   ├── evidence/                 # SHA-256 recorder & markdown reporter
│   │   ├── jobs/                     # Atomic SQLite job worker
│   │   └── api/                      # REST endpoints under /api
│   └── tests/                        # Unit, integration, and e2e tests
├── apps/
│   └── web/                          # Next.js App Router + HTML5 Canvas
├── scenarios/
│   ├── reference/                    # Canonical RW-REF-001 scenario
│   ├── regression/                   # 3 critical regression cases
│   ├── library/                      # 10 selectable test scenarios + catalog.json
│   └── holdout/                      # Frozen 20-scenario manifest
├── scripts/
│   ├── bootstrap.ps1 / bootstrap.sh  # Environment bootstrap scripts
│   ├── smoke_test.py                 # Fast schema & import validator
│   ├── verify_evidence.py            # Independent SHA-256 evidence verifier
│   └── run_offline_demo.py           # Offline reference demonstrator
└── artifacts/                        # Run and verification evidence output
```

---

## 3. Local Installation & Startup

### Step 1: Environment Setup
Using PowerShell on Windows:
```powershell
.\scripts\bootstrap.ps1
```

Or manually:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### Step 2: Running Services
**Terminal A: FastAPI Backend**
```powershell
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal B: Background Jobs Worker**
```powershell
cd backend
.\.venv\Scripts\python.exe -m app.jobs.worker
```

**Terminal C: Next.js Frontend Dashboard**
```powershell
cd apps/web
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. Running Tests & Verifications

```powershell
# Run smoke test
python scripts/smoke_test.py

# Run backend unit tests
cd backend
pytest -v

# Run frontend checks
cd ../apps/web
npm run lint
npm run typecheck
```

---

## 5. Offline Reference Mode
RoboWitness functions fully offline without any paid Meta API keys. When `RW_AI_MODE=offline` is set in `.env`, the system serves validated offline reference scenarios and investigations labeled with `OFFLINE_REFERENCE` provenance.

### Windows note: PyBullet from source
PyPI ships no `cp311` Windows wheel for `pybullet==3.2.5`, so Windows installs
compile it with MSVC 2019+ (Build Tools are sufficient):
```powershell
& "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
$env:DISTUTILS_USE_SDK=1; $env:MSSdk=1
python -m pip install wheel setuptools
python -m pip install --no-build-isolation pybullet==3.2.5
```

## 5b. Robot Catalog & Scenario Library

The Test tab includes a **robot catalog**: pick a robot by brand/model
(ROBOTIS TurtleBot3, Clearpath Jackal, MiR250, Spot, Go2, …), see its specs
(drive type, body radius, wheels, weight, payload, sensor type/range/latency/
noise, compute, OS, battery), or **add your own robot** with the same fields
(edit/delete supported; brand+model+variant must be unique). Builtin specs are
nominal example values, not manufacturer-certified measurements. “Seçili Robotu
Teste Uygula” copies only the physical/sensor fields into the scenario's
`RobotSpec`; start/goal stay scenario-owned. Robots the differential-drive
simulator cannot represent (non-differential drive, body radius outside
0.15–0.40 m) remain catalog-only and are honestly marked incompatible.

Next to it, a **scenario library** offers 10 extra test scenarios
(`RW-LIB-001…010`: narrow corridor, slalom, head-on, crossing, 800 ms latency,
noisy sensor, dual moving obstacles, empty-corridor control, slow traffic)
via `GET /api/scenarios/library`; robot CRUD lives under `/api/robots`.
Measured baseline results for the library are recorded in
`docs/IMPLEMENTATION_STATUS.md`.

## 5c. Exam Battery, Policy Profiles, Real-Log Import

- **Robot exam (Karne tab):** pick a catalog robot + a policy profile, run the
  default battery (reference + 10 library scenarios) with one click, and get a
  report card — per-scenario PASS/FAIL, collisions, near-misses, worst
  clearance — with per-run replay and a downloadable Markdown report
  (`GET /api/batteries/{id}/report.md`). Measured example (TurtleBot3 Waffle Pi,
  baseline profile): 4/11 passed, 5 collisions, 2 near-misses.
- **Policy profiles:** named presets for the 5 policy parameters
  (`/api/policy-profiles`): 4 builtins plus your own saved profiles, selectable
  in the Düzeltme tab and in the battery.
- **Your own policy code (opt-in):** with `RW_ALLOW_LOCAL_POLICY=on`, single-file
  Python policies you wrote in `backend/app/policies/local/` (see
  `example_policy.py`) can drive single runs and the battery. They execute in a
  separate subprocess with timeouts and clamped outputs; plugin errors fail the
  run honestly. This is **not** a security sandbox — trusted own code only, and
  AI-generated code is forbidden there.
- **Real-log import:** upload a real robot drive (CSV
  `t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m` or JSON frames) in the Karne
  tab; it is judged by the same collision/clearance/goal rules and labeled
  `REAL_LOG` — measured elsewhere, not simulated here. A passive ROS 2 recorder
  (`scripts/ros2_bridge.py`, listens only, never publishes) can produce such
  logs on a ROS machine.

## 6. Measured verification status (2026-10-30, frozen holdout set v4)
- **Path A (failure detected):** baseline `RW-REF-001` deterministically `FAIL`s
  (`COLLISION` at tick 358, 3/3+ identical repeats, bit-identical after controller upgrade).
- **Path C (rejection demonstrated):** over-cautious candidate honestly `REJECTED`
  (paired `TIMEOUT`/`GOAL_NOT_REACHED`, holdout + regression failures).
- **Path B (improvement accepted): UNMET.** Four frozen eval sets (v1 dev 20/20 → v2/v3 17/20 → v4 **18/20**),
  shared-law upgrades (delivered-velocity estimator, direction-space avoidance blending,
  anti-sitting-duck creep, obstacle-speed influence — baseline bit-identical throughout),
  60-case dev best 59/60. Verdicts honestly `REJECTED`. See `docs/DEMO_GUIDE.md` and
  `docs/IMPLEMENTATION_STATUS.md` for exact commands, IDs, and artifacts.
