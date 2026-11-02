# RoboWitness Implementation Status

Governed by `ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md`. All results below are
measured in this session — no unattended claims, no fabricated verdicts.

## Phase Checklist

| Phase | State | Deliverables | Exact verification command | Actual result (2026-10-30) |
|---|---|---|---|---|
| PHASE 01 | PASS | Architecture, env, contracts, schemas, health endpoint | `python -m pytest -q` (backend) | 46/46 pass (incl. 8 original). Reference fixture parses; OpenAPI serves. |
| PHASE 02 | PASS | PyBullet DIRECT world, kinematics, delayed sensor queue, runner | `python scripts/run_offline_demo.py` + `test_simulation.py` (8 tests) | PyBullet 3.2.5 source-built with MSVC 2019 (no cp311 win wheel on PyPI). Real telemetry JSONL from DIRECT steps; 0.05 s per 359-tick run. Policy unified to single shared nav law; horizon bug fixed. |
| PHASE 03 | PASS | Independent oracle + frozen reference failure | `test_oracle.py` (7 tests) + 3x repeat run | Baseline `FAIL` repeats 3/3 identical: `COLLISION` tick 358, min_clear 0.0016. PASS/FAIL/INCONCLUSIVE all demonstrated by tests. |
| PHASE 04 | PASS | SQLite jobs, runs, atomic claim, API+worker, run evidence | `test_jobs.py` (6) + `test_evidence.py` (4) | Atomic single-owner claim, cancel flow, 404/422 contracts, tamper/missing-member detection. Real run `run-697c157aee28` persisted; integrity re-check OK. |
| PHASE 05 | PASS + LIVE (2026-10-30) | Real Meta transport, both endpoints live | `test_ai_live.py` (7 mock tests incl. fix-hint regenerate, no creds) + live probes via running backend | Host api.meta.ai `/v1`, Bearer 200, 9 served models incl. `muse-spark-1.3-contributor`. `POST /generate` -> 200 LIVE_META (new validated scenario). `POST /failures/{id}/investigate` -> 200 LIVE_META (measured tick honored, whitelist patch keys). Strict Pydantic + one controlled regenerate; UNAVAILABLE otherwise. Offline fallback + conftest offline-forcing preserved. |
| PHASE 06 | PASS (v3 desktop-program rewrite 2026-11-01) | apps/web masaüstü programı düzenine çevrildi: pencere başlık/menü/araç çubuğu + sol adım listesi + sekmeli sağ panel + durum çubuğu, sayfa kayması yok, sade Türkçe arayüz, teknik terimler katlı "Teknik detaylar" altında; aynı doğrulanmış bağlantılar ve buton kimlikleri korundu, katı siyah/beyaz/gri palet korundu | npm run lint+typecheck+build + live browser proof |
| PHASE 07 | PASS | Grounded investigation + candidate UI | `test_jobs.py::test_investigation_grounded_in_measured_telemetry` | Investigate reads recorded `telemetry.jsonl`/`metrics.json`: measured tick 358 + real clearance numbers; unknown run → 404. UI FailureAnalysis wired with provenance + apply-patch. |
| PHASE 08 | PASS | Paired comparison + reproduction gate | `test_verification.py` (hash tests) + measured runs | Gate 1 reproduces baseline FAIL from immutable scenario; Gate 2 compares identical scenario_hash with distinct policy hashes. Same-policy repeat stable. |
| PHASE 09 | PASS — Path B CLOSED 2026-11-02 | Frozen 20 holdouts, regressions, sealed verdict | `run_final_evaluation.py` + `test_verification.py` | v2–v5 sets: candidate-final-v1 (shared law) 17–18/20 → REJECTED each time, honestly. Then MPC candidate law (developed on the 80 burned cases, 80/80) + pre-registered fresh v6: `verif-6b2bfd8e0501` **VERIFIED_IN_SIMULATION** (Gate 3 20/20, all gates PASS, seal re-verified). See `docs/PATH_B_V6_PREREGISTRATION.md`. |
| PHASE 10 | PASS | Verification UI, paired replay comparison, rejection demo + 3D viewer | In-app browser flow + `test_verification.py` | 2026-10-30 live UI run: baseline (359 FRAMES) → Investigate (measured tick 358) → Apply patch → Verify → REJECTED with real gates. `ComparisonReplay` renders sealed baseline+candidate side-by-side (`BASE 359 / CAND 1340 FRAMES`, delta `0.0016 → 0.7575 m`). Rejection demo: over-cautious + pre-registered candidates honestly REJECTED. Services left running: backend :8000, worker, web :3000. 3D viewer (Three.js, display-only, physics untouched) verified live: WebGL2 canvas, zero console errors. |
| PHASE 11 | PASS | Sealed evidence, download, independent verification | `python scripts/verify_evidence.py artifacts/verifications/<id>` | 3/3 packages verify (`verif-19161efb3b2c`, `verif-c15a43a8b39a`, `verif-61f504916d9e`). Safe ZIP download tested. Gate-5 reseals + re-verifies sealed bytes; failure → INCONCLUSIVE (implemented + tested structurally). |
| PHASE 12 | IN_PROGRESS | Fresh install, hardening, final demo | `run_offline_demo.py` PASS; bootstrap updated | Demo runs real sims end-to-end (FAIL/PASS/FAIL). Fresh-install from venv NOT_RUN in this session (env pre-existed); bootstrap.ps1 updated for MSVC/wheel. Worker heartbeat now truthful (`worker_active` from heartbeat file, stale >30 s → false). |

## Extension — Robot Catalog + Scenario Library (2026-11-01, user request)

Beyond blueprint Phases 01–12, added per user request (“daha fazla test
senaryosu” + “robotların marka/model/özelliklerini girebildiğimiz, yeni robot
ekleyebildiğimiz sistem”):

- **Robot catalog (backend):** `app/schemas/robot_profile.py` (brand, model,
  variant, year, drive type, body/wheel geometry, weight, payload, max speed,
  sensor type/range/latency/noise, compute, OS, battery, notes),
  `app/robots/catalog.py` (6 builtin example robots: ROBOTIS TurtleBot3 Waffle
  Pi + Burger, Clearpath Jackal, MiR250, Boston Dynamics Spot, Unitree Go2 —
  labeled nominal example values, not manufacturer-certified),
  `app/robots/repository.py` + SQLite `robots` table (user robots),
  `app/api/routes_robots.py`: `GET/POST /api/robots`, `GET/PUT/DELETE
  /api/robots/{id}` (duplicate brand+model+variant → 409, builtin edit/delete
  → 403, unknown → 404), `POST /api/robots/{id}/apply-to-scenario`.
  Honest sim gate: only `differential_drive` + body radius 0.15–0.40 m are
  `simulation_compatible`; others stay in catalog with machine-readable
  `compatibility_issues` and apply → 422 `ROBOT_NOT_SIM_COMPATIBLE`. Apply maps
  only body/wheel/sensor fields into `RobotSpec`; start/goal stay scenario-owned.
- **Scenario library:** `scenarios/library/` 10 new cases (RW-LIB-001…010:
  dar koridor, slalom, diyagonal, karşıdan gelen, çapraz kesme, 800 ms gecikme,
  gürültülü sensör, çift hareketli, boş koridor kontrol, yavaş trafik) +
  `catalog.json` (title/description/difficulty/category/tags) served by
  `GET /api/scenarios/library`. Frozen holdout sets untouched.
- **Measured baseline outcomes (real PyBullet runs, baseline-v1 policy):**
  PASS: RW-LIB-001, RW-LIB-009, RW-LIB-010. FAIL: RW-LIB-002/005/006
  (MIN_CLEARANCE_VIOLATION, goal reached), RW-LIB-003/004/007/008 (COLLISION).
- **Frontend:** Test tab now has `ScenarioLibrary` picker + `RobotPanel`
  (robot select with specs + compatibility, add/edit/delete user robot form,
  “Seçili Robotu Teste Uygula”). Applied robot label shown above the panels.
- **Verification:** backend `69 passed` (was 59; +10 new in
  `tests/unit/test_robots.py` + `test_scenario_library.py`), ruff `--select E,F`
  + format clean, web lint+typecheck+build clean. Live: created user robot via
  API → applied to RW-LIB-009 → real worker run `run-dd362be9f691` PASS
  (773 ticks); browser proof on dev stack (library 11 options, robot 6 options,
  apply + add-robot flows, 0 console errors). Services restarted on new code:
  backend :8000, worker (heartbeat fresh), web :3000.

## UI Simplification (2026-11-01, user request “arayüzü sadeleştir”)

- Removed fake window controls + menubar (Help moved to titlebar), removed the
  duplicated left step sidebar (steps remain as right-panel tabs + toolbar
  “Sıradaki adım”), removed sidebar help boxes and the welcome box.
- Workspace is now 2 columns (simulation + 380 px inspector). Test tab's three
  stacked cards became three compact sections separated by hairlines:
  `Senaryo` (one-line mono summary + Çalıştır + two small buttons),
  `Senaryo Kütüphanesi (10)` (select + one-line description), `Robot`
  (select + one-line summary + compatibility badge + Teste Uygula; add/edit
  form stays collapsed under “Yeni robot ekle”). All button/select IDs preserved.
- Verification: web lint+typecheck+build clean; live browser check — no
  menubar/sidebar/wincontrols in DOM, robot+library selects present, sections
  stack without overlap (185/83/216 px), no horizontal overflow, 0 console
  errors. Frontend restarted on :3000 with the new layout.

## Run Verdict Gate (2026-11-02, user report: PASS runs still went to “Hata”)

Root cause: the oracle existed (`app/verification/oracle.py`: collision,
clearance, goal, timeout, stuck → PASS/FAIL/INCONCLUSIVE, stored per run) but
the UI never read it — `page.tsx` unconditionally jumped to the Hata tab after
any run, and `POST /failures/{id}/investigate` investigated even PASS runs.

- Backend: investigate now refuses non-FAIL runs with `409 RUN_DID_NOT_FAIL`
  (oracle status read from `runs` table). New tests
  `tests/unit/test_run_verdict.py` (PASS/INCONCLUSIVE → 409, FAIL → 200).
- Frontend: after a run, UI fetches `GET /api/runs/{id}` and shows
  `RunVerdict` banner (“KAZASIZ TAMAMLANDI ✓” / “KAZA OLDU ✗” / “KARAR
  VERİLEMEDİ” + reason labels, min clearance, goal, duration). Step flow is
  oracle-driven: only FAIL advances to Hata; PASS stays on Test with
  “Test kazasız tamamlandı…” guidance. FailureAnalysis and FixComparison are
  gated on an actual FAIL baseline; verdict restored for saved/history runs.
- Verification: backend `72 passed`, ruff E,F clean; web lint+typecheck+build
  clean. Live: RW-LIB-009 → oracle PASS, investigate HTTP 409; RW-REF-001 →
  FAIL (COLLISION tick 358 class), investigate 200. Browser: PASS run shows
  KAZASIZ TAMAMLANDI and stays on “1. Test”; FAIL run jumps to “2. Hata”;
  0 console errors. Backend :8000 restarted with the guard.

## Near-Miss Clarity (2026-11-02, user report: “simülasyon başarılı bitti ama 2. sekme hatayı incele diyor”)

Measured root cause: RW-LIB-002/005/006 reach the goal with **no collision**
but `min_clearance_m` 0.15/0.152/0.173 < oracle limit 0.25 m →
`FAIL [MIN_CLEARANCE_VIOLATION]`. Visually a success, formally a failed
near-miss; the UI only said “BAŞARISIZ / Hatayı incele”, so the reason was
invisible. Fixes (frontend only, oracle unchanged):

- `RunVerdict` FAIL branch now distinguishes near-miss: “HEDEFE ULAŞTI AMA
  GÜVENLİ DEĞİL ✗ — Çarpışma olmadı… engele en yakın 0.15 m… izin verilen
  0.25 m…” (viewport banner + İncele tab).
- Step/tab 2 renamed “Hata” → “İncele”; toolbar + investigate button say
  “Yakın Geçişi İncele” for near-miss and spell out both numbers; FailureAnalysis
  intro adapts and re-shows the verdict.
- Replay legend now shows live per-frame clearance with a “Güvenli sınırın
  altında” badge when below the limit, so the violating moment is visible.
- Live browser proof (Slalom RW-LIB-002): verdict appears in both places,
  toolbar reads “Çarpışma olmadı ama robot engele 0.15 m yaklaştı (güvenli
  sınır: 0.25 m)…”, 0 console errors. Web typecheck+build clean.

## Product Plan Implementation (2026-11-02, plan: ~/.opencode/plan/robowitness-urun-plani.md)

Implemented in plan order. İş 3B was initially deferred; the user explicitly
approved it on 2026-11-02 and it is now implemented too (see below).

- **3A Policy profiles:** `policy_profiles` table + `/api/policy-profiles` CRUD
  (4 builtin presets: baseline/Dengeli/Temkinli/Hızlı; user profiles, duplicate
  name 409, builtin 403). UI: “Ayar Profilleri” in Düzeltme tab (select applies
  to sliders, save-current, delete).
- **İş 1 Battery / report card:** `battery_runs` table, job kind `battery_run`
  (worker dispatches it), `/api/batteries` (POST 202 / GET / list /
  `/{id}/report.md`). Default battery = RW-REF-001 + 10 library scenarios with
  the chosen robot applied. Each entry persists a real run (replay works from
  the card). Live measured (Waffle Pi + baseline, 6.5 s): **4/11 PASS,
  5 collisions, 2 near-misses, worst clearance 0.003 m** — note RW-LIB-006
  passes here because the robot profile's 100 ms sensor latency replaces the
  scenario's 800 ms (robot's own sensor wins; documented behavior).
- **İş 2A Real-log import:** `/api/imports/telemetry` (CSV + JSON, ≤20k frames,
  monotonic-time checked) judged by `log_oracle` with the same rules; stored in
  `telemetry_imports`, provenance `REAL_LOG`. Live: near-miss CSV → FAIL
  near_miss=true min 0.10 m. UI: “Gerçek Sürüş Yükle” in Karne tab.
- **İş 2B ROS 2 bridge (passive):** `scripts/ros2_bridge.py` listens to
  /odom+/scan only, never publishes; without rclpy it exits 2 with an honest
  [BLOCKED] message (verified on this machine — no ROS installed, so live ROS
  is UNVERIFIED). Pure converters in `app/ros_bridge/format.py` unit-tested.
- **Verification:** backend **91 passed** (was 72; +19: profiles 4, batteries 4,
  imports 5 incl. ROS helpers, local policies 6), ruff E,F + format clean; web lint+typecheck+
  build clean. Browser: Karne tab ran the full battery in UI (4/11, download
  button, profile select 5 options), 0 console errors. Backend+worker
  restarted on new code (:8000, heartbeat fresh).
- **İş 3B Local user policy (approved 2026-11-02):** single-file Python policies
  in `backend/app/policies/local/` (`policy(observation, config)` contract,
  `example_policy.py` template) run in a dedicated subprocess
  (`plugin_host` + `SubprocessPolicy`): per-call 5 s timeout, crash containment,
  outputs validated/clamped to ControlCommand limits; plugin errors fail the
  job honestly. Gate: `RW_ALLOW_LOCAL_POLICY` (default off; enabled in this
  machine's `.env` by user approval, test suite forces it off and opts in
  explicitly). Usable from Test tab (“Kendi Kodum”) and battery. NOT a security
  sandbox — trusted own code only, AI-generated code forbidden (stated in UI,
  `.env.example`, and folder README docstring). Verification flow (5-param
  candidate) intentionally unchanged. Live: example policy on RW-LIB-009 →
  PASS 773 ticks; path-traversal name → 404; 6 new tests in
  `tests/unit/test_local_policies.py`.
- **Remaining / honest gaps:** ROS live path unverified (no ROS on this
  machine); Path B still unmet (no candidate has passed all 20 frozen
  holdouts — best 18/20).

## Enterprise Layer (2026-11-02, user: “enterprise seviyeye çıkar, her şeyi onaylıyorum”)

Full guide: `docs/ENTERPRISE.md`. Implemented + live-verified:

- **Auth/RBAC/workspace:** opt-in API keys (`RW_API_KEYS=key:role:workspace;…`),
  roles admin>editor>viewer, `X-API-Key` middleware (health public, OPTIONS
  exempt), workspace isolation for user robots, policy profiles, batteries and
  telemetry imports (builtin catalogs shared). Frontend stores key/workspace in
  localStorage (titlebar inputs) and sends them on every API call.
- **Audit + metrics:** every write lands in `audit_logs` (actor/role/workspace/
  path/status); `GET /api/audit` (admin), `GET /api/metrics` (workspace counts,
  last battery summary, import pass/fail, job states).
- **Battery compare:** `GET /api/batteries/compare?a&b` + Karne UI (A/B selects,
  İYİLEŞTİ/KÖTÜLEŞTİ/AYNI per scenario, clearance deltas).
- **Map import (own environment):** `POST /api/maps/scenario` converts an
  occupancy grid (`#`/`.`/`S`/`G`) to a validated scenario (connected clusters
  → circle obstacles, ≤8, clamp warnings); UI in Test tab. Live: sample salon
  → `RW-MAP-54b2d2`, 1 obstacle, 12×6 m.
- **CI gate:** `scripts/ci_battery_gate.py` (exit 0/1/2) over threshold logic
  `app/verification/battery_gate.py`. Live: lax thresholds → exit 0
  (4/11, collisions 5); strict (1.0/0) → exit 1 with printed reasons.
- **Live auth proof:** no key → 401, viewer reads metrics, health public.
  Demo keys were only for the live check; running backend was restarted in
  open local mode so the UI keeps working (enable via `.env` when wanted).
- **Verification:** backend **98 passed** (+7 enterprise tests: auth/RBAC,
  workspace isolation, audit/metrics, maps, gate), ruff E,F + format clean;
  web lint+typecheck+build clean; browser proof (map convert notice, compare
  button, API-key inputs), 0 console errors.
- **Honest limits (also in ENTERPRISE.md):** SQLite single-file (logical
  tenancy, not sharded), API-key auth only (no SSO/OIDC), simple physics —
  report cards are not real-world safety certification; Path B still unmet.

## Enterprise Round 2 (2026-11-02, user: “eksik olanları ekle”)

Closing the gaps honestly listed after the first enterprise round:

- **Sensor occlusion:** obstacles hidden behind a closer obstacle are no
  longer observed (`_is_occluded` in sensors.py + 2 tests). Gate check:
  RW-REF-001 baseline outcome bit-preserved (FAIL, min 0.0016, offline demo
  Path A OK); library battery outcomes re-measured — unchanged.
- **JWT/OIDC auth:** HS256 (`RW_JWT_SECRET`) and OIDC RS256 via JWKS
  (`RW_OIDC_JWKS_URL`, optional iss/aud) bearer tokens, claim→principal
  mapping, expired/tampered/wrong-secret → 401 (6 tests incl. generated RSA
  key, monkeypatched JWKS — live OIDC IdP itself UNVERIFIED, no IdP here).
- **Workspace backup:** `GET /api/workspaces/export` + `POST
  /api/workspaces/import` (admin) with no-overwrite history semantics.
- **Trend:** `GET /api/batteries/trend` + Karne chart strip.
- **Fleet battery:** `POST /api/batteries/fleet` (per-robot jobs, skipped
  with reasons) + ranked Karne UI.
- **Verification:** backend **105 passed** (+7 round-2 tests), ruff clean;
  web lint+typecheck+build clean. Live: locally minted HS256 token → 200;
  fleet (Waffle+Jackal run, Spot skipped with reasons); trend 7 points;
  browser Karne shows trend + fleet + JWT input, 0 console errors. Backend
  restarted in open local mode (JWT secret was live-check only).
- **Still honestly open at that time:** SQLite logical tenancy (no sharding), no IdP
  session management, kinematic 2D physics (occlusion added; no beam-level
  LiDAR), Path B then unmet (best 18/20 frozen holdouts). Path B was later
  closed on 2026-11-02 — see the PATH B CLOSED section below.

## Enterprise Round 3 — Platform Layer (2026-11-02, user: “durmak yok”)

- **DB API keys:** CRUD under `/api/admin/api-keys` (hash-only storage,
  one-time plaintext, revoke). First-key-must-be-admin lockout guard (422) —
  found live when a viewer-first key locked the operator out; live DB cleaned
  and guard added. Keys enforce auth as soon as one exists.
- **Hardening:** Idempotency-Key on run/battery creation (retries return the
  same job), per-actor rate limiting (`RW_RATE_LIMIT_PER_MIN` → 429),
  X-Request-Id + nosniff/DENY headers on every response.
- **Webhooks:** HMAC-signed `job.completed`/`battery.completed` (tested with
  captured request + signature recomputation; failures never fail jobs).
- **Schedules:** recurring batteries (`/api/batteries/schedules`, worker
  enqueues due ones once, no catch-up storm) + Admin UI.
- **Ops:** WAL-safe DB backup with SHA-256, retention (dry-run default, sealed
  evidence untouched), Prometheus `/api/prom`, worker concurrency
  (`RW_WORKER_CONCURRENCY`, atomic claim keeps single-owner).
- **Admin UI:** new “Yönetim” tab — system metrics, DB backup, API keys,
  schedules, audit trail.
- **Verification:** backend **113 passed** (+8 round-3 tests), ruff clean; web
  lint+typecheck+build clean; live headers/prom/backup/key-lifecycle proven;
  browser Admin tab verified. NOTE: `npm run build` while the dev server ran
  corrupted `.next` once (3000 → 404); dev server restarted, healthy.

## Enterprise Round 4 + Path B v5 (2026-11-02, user: “devam”)

- **Beam LiDAR mode:** `RW_SENSOR_MODEL=beam` (default legacy; all frozen
  results use legacy). 24-ray casting with quantized bearing; obstacles
  between rays are missed like a real scanner. Measured on the library with
  baseline: same PASS/FAIL pattern as legacy (LIB-005 min clearance
  0.1492 vs 0.152 in legacy). Baseline gate preserved.
- **Backup restore:** `POST /api/admin/restore` (pre-restore safety copy +
  SHA-256 of restored file; path traversal → 404), tested round-trip.
- **Docker:** `Dockerfile.backend`, `Dockerfile.web`, `docker-compose.yml`
  (config validates). Docker Desktop was started on this machine; backend
  image built + ran healthy (6 robots), web image built + served 200.
  Daemon was unstable (died twice, restarted) — noted, images verified.
- **Path B v5 (pre-registered, single shot):** see
  `docs/PATH_B_V5_PREREGISTRATION.md`. Frozen v5 generated (RW-HLD5-*,
  v4 archived byte-exact). `candidate-final-v1` → `verif-ec5ae352765d`
  **REJECTED, Gate 3 = 18/20** (HLD5-008 clearance+stuck+timeout,
  HLD5-016 stuck-despite-goal). No re-roll, per pre-registration. Path B
  remains open; the honest next step is a richer controller family
  (anti-stuck) + a fresh pre-registered v6, not another set today.
- **Verification:** backend **117 passed** (beam 4 + restore round-trip),
  ruff E,F clean; services on legacy sensor mode.

## Controller Experiment — pass-behind avoidance (2026-11-02, measured, REVERTED)

Goal: fix the two stuck failures (HLD5-008/016). Diagnosis from telemetry:
in 016 the robot retreats along the obstacle sweep at creep speed for ~9 s
with no goal progress — radial escape is the stall. Experiments (candidate
F1 params, 80 burned cases v1+v2+v3+v5):

| Law variant | Total | Failures |
|---|---|---|
| Original (current) | 77/80 | 017 collision, 008, 016 stuck |
| Progress creep floor | 77/80 | same set (008 clearance worse) — reverted |
| Pass-behind bias 0.4 | 76/80 | 017, 008, 013, 016 — reverted |
| Pass-behind bias 0.7 | 77/80 | 017, 008, 013 collision (016 fixed) — reverted |
| Pass-behind bias 1.0 | 77/80 | 017, 008 collision, 013 — reverted |

No variant dominates; failures rotate among {017, 008, 013, 016}. This law
family + 350-400 ms latency has hit its ceiling. The law is left byte-identical
to the measured baseline (offline demo: FAIL tick class unchanged, 117 tests
green). Also noted: the v5 set's geometry turned out identical to v4's (same
recipe seed sequence; only sensor-noise seeds differed) — recorded here so
nobody mistakes v5 for fully independent geometry. A future attempt needs a
structurally different controller (e.g., timed gap-crossing planner), a new
pre-registration, and a genuinely fresh recipe seed for v6.

## Controller Experiment Round 2 — timed gap-crossing planner (2026-11-02, REVERTED)

Implemented and measured three structural variants on the same 80 burned
cases (candidate F1 params; original law = 77/80):

| Variant | Total | Note |
|---|---|---|
| Timed gap-rush (speed floor only) | 77/80 | fired 129 ticks in 016, still stuck (wrong heading) |
| Gap-rush + committed goal heading | 77/80 | identical failures {017, 008, 016} |
| Stall-gated pass-behind (0.7 @ low speed) | 74/80 | new collisions (HLD3-016, HLD5-013) |

Diagnosis (016): stuck first trips at tick 679 with the robot south of the
sweeping obstacle — a pass-side commitment problem, and every steering bias
tried either does nothing or trades a stuck for a collision. All variants
reverted: `configurable.py` is byte-identical to the measured baseline
(offline demo FAIL class unchanged; policy/simulation tests green).
Conclusion stands: this needs a stateful planner (side commitment with
memory), which the current stateless policy contract does not allow —
that is a contract change, to be pre-registered separately if attempted.

## Stateful Candidate Planner (2026-11-02, opt-in experimental, NOT an improvement claim)

Contract change, kept: `SimulationRunner` calls `policy_fn.reset()` per run;
candidate policy selection is centralized in `app/policies/candidate_law.py`
(`RW_CANDIDATE_LAW=shared|stateful`, default **shared** — every frozen result
unchanged). Holdout/regression/paired-candidate paths use the selector;
baseline always uses the shared law.

Measured on the same 80 burned cases (candidate F1 params):
- Proactive side-commitment planner: **65/80** (virtual-goal shift dragged
  healthy runs into stalls) — rejected.
- Reactive variant (detour shift + creep floor only after ~1–1.5 s of stall):
  **77/80**, failures identical to the shared law {017 collision, 008, 016};
  no regression, no gain (008 clearance 0.116 → 0.170, still FAIL).

Verdict: shipped as an experimental opt-in (`stateful_candidate.py`, 5 unit
tests) because the contract plumbing is the honest prerequisite for future
controller research — but Path B is NOT advanced by it, so no v6 set was
generated: running a fresh set with an unimproved candidate would be set
shopping. Backend 122 passed; default behavior byte-identical.

## Waypoint Candidate Planner (2026-11-02, opt-in experimental, NOT an improvement claim)

`RW_CANDIDATE_LAW=waypoint`: picks one world-frame waypoint beside the
blocking obstacle (vacating side), steers there via the shared core law,
resumes to goal on reach; v2 added stale/unsafe waypoint re-planning
(300-tick expiry, obstacle-swept-back detection). Measured on the same 80
burned cases: **68/80** both versions (shared law: 77/80). Failure mode:
core-law braking near the waypoint lets the oracle's 3 s stuck window close
before the waypoint is reached — the same wall every candidate-side idea
hits. Kept as a tested, opt-in experimental law; default remains `shared`.
Backend 126 passed. Honest summary across all controller attempts: with
350–400 ms latency and this oracle, the shared law's 77/80 (best frozen
result 18/20) is the current ceiling; beating it likely needs prediction
quality (track fidelity under latency), not more steering heuristics.

## PATH B CLOSED — First VERIFIED (2026-11-02)

`verif-6b2bfd8e0501` → **VERIFIED_IN_SIMULATION** (all 5 gates PASS, Gate 3
20/20 on the fresh, pre-registered v6 set; independent seal re-check OK).
Pre-registration: `docs/PATH_B_V6_PREREGISTRATION.md` (written before the
set existed). Winning change: **MPC-lite candidate law**
(`app/policies/mpc_candidate.py`, `RW_CANDIDATE_LAW=mpc`): receding-horizon
rollouts over delivered tracks with a preferred-clearance tier (0.28 m).
Development was on the 80 burned cases (80/80 there: v1-dev 20, v2 19→20,
v3 20, v5 19→20), regressions 3/3. Over-cautious control still REJECTED
(`verif-3b370a934cfc`). A worker race produced an extra shared-law data
point on v6 (`verif-1db21e6713ad`, 18/20 REJECTED) — recorded in the
pre-registration doc; the MPC shot itself was single and pre-registered.
Default law remains `shared`; MPC is the verified candidate configuration
to enable explicitly. Path B is no longer an open gap.

Verification for this round: backend **129 passed** (new MPC/stateful/waypoint
tests), `ruff check --select E,F` clean, `ruff format --check` clean
(112 files).

## Release 1.0.0 Stabilization (2026-11-02, user decision: freeze features)

Full record: `docs/RELEASE_1.0.0.md`. Summary: versions bumped to 1.0.0
(pyproject, package.json, API title). Suite stable twice (129/129), ruff +
web gates clean, smoke + offline demo measured. Fresh-venv install went
129/129 after fixing two real defects found only by stabilization:
undeclared `cryptography` dependency (OIDC would silently fail) and missing
`numpy` in the Docker image (worker import crash). Compose triple verified
end-to-end (battery 1/1 inside containers), then torn down; local services
restored. No new features added in this round. Suggested tag: `v1.0.0`.

## Ultra Showcase Pack (2026-11-02, hackathon demo asset)

5 ultra scenarios (`scenarios/ultra/` + catalog, served inside
`/api/scenarios/library`, difficulty "Ultra"; battery default now 16
scenarios). Frozen expectations in `tests/unit/test_ultra_scenarios.py`:
baseline FAILs all 5 (collisions/near-misses); Meta-style patch + MPC
passes all 5. Live proof with real Meta: ULTRA-002 baseline collision →
LIVE_META investigation (tick 283) → patch (0.45/0.85/0.15/3.0/0.6) →
verification `verif-e691c7dc3096`: Gate 2 PASS (solves the ultra paired
run) but Gate 3 19/20 (RW-HLD6-013 STUCK) → REJECTED. The champion
configuration (candidate-final-v1 params + MPC) remains the only VERIFIED.
Worker restarted with default (shared) candidate law afterwards.

## End-to-End Test Suite (2026-11-02)

`backend/tests/integration/test_e2e_journeys.py` — 5 full journeys through
HTTP + real worker service + oracle + sealed evidence (no mocks):
1. Failure → investigation → over-cautious verification REJECTED → evidence
   ZIP + independent seal check.
2. Custom robot → 2 batteries → report card → replay → compare → trend.
3. Own map → scenario run; real-log near-miss; metrics + audit views.
4. DB API-key lifecycle end-to-end (401/viewer-403/open-again).
5. **MPC configuration earns VERIFIED_IN_SIMULATION on frozen v6**
   (Gate 3 20/20, seal re-verified) — 69 s.
Suite total: **136 passed** (~100 s). Plus `scripts/e2e_live_stack.py`
against the running stack: ALL PASSED (investigation answered LIVE_META).

## Crowd Pack + Crowd MPC (2026-11-02, user: crowded traffic/people)

5 crowd scenarios (`scenarios/crowd/`, in the library; battery now 21):
crossing streams, two-way corridor, goal guards, market chaos, fast
pedestrians (0.8-0.9 m/s, 500 ms latency). New law `mpc-crowd`
(`RW_CANDIDATE_LAW=mpc-crowd`): closed-loop rollouts (heading re-aimed
every simulated step), prediction-uncertainty inflation, 3.6 s horizon.
Frozen contract (`tests/unit/test_crowd_scenarios.py`): baseline fails
5/5; champion (candidate-final-v1 params + crowd law) passes 5/5 with
0.36-0.76 m clearances. The verified `mpc` law is untouched (v6 re-check
still 20/20). Live: Pazar Yeri baseline collision → verification with the
crowd configuration → `verif-b9ce2a55155e` **VERIFIED_IN_SIMULATION**
(all gates incl. Gate 3 on v6 also pass under the crowd law).
Caught in passing: a stale pre-crowd worker process was stealing jobs —
killed; worker restarted on the default shared law. Suite: 138 passed.

## Perfection Pass — Test Gaps Closed (2026-11-02, user: “hatasız mükemmel olmalıyız”)

- Dead code deleted (`ai/investigator.py`, `ai/scenario_generator.py`,
  `ai/prompts.py` — unreferenced; the adapter is self-contained).
- 15 new backend tests: run metrics/oracle edges, job repository claim
  semantics, worker loop success+failure with stubbed service (26% → covered
  paths), plugin host subprocess protocol (was 0% direct), example policy,
  local-policy timeout abort, map warning caps, JWT issuer mismatch.
- Frontend E2E (Playwright, `apps/web/e2e/journeys.spec.ts`, 5 tests, live
  stack): grouped library (Kalabalık/Ultra), crowd crash verdict, clean
  PASS does not advance, Karne controls, Admin controls — **5 passed**.
  It caught a REAL product bug: the initial reference-scenario load could
  clobber a scenario the user had already selected (fixed with a
  `prev ??` guard in page.tsx).
- Coverage: backend 88% → **90%**, suite **153 passed**. Ruff + lint +
  typecheck clean. Remaining honest limits are unchanged (live IdP/ROS
  never available here; physics 2D; single-node SQLite).

## Rock-Solid Hardening (2026-11-02)

- **Job lease recovery (real robustness gap, closed):** claimed jobs now
  carry a lease (`RW_JOB_LEASE_SECONDS=600`, renewed by progress updates);
  a job whose worker died mid-flight is automatically reclaimed to the
  queue by the next claim instead of hanging in `running` forever.
- **Concurrent-claim proof:** 5 threads × 10 jobs — each claimed exactly
  once (atomic BEGIN IMMEDIATE claim holds under contention).
- **Hostile-input suite:** bad types → 422 envelope, 20 001-frame import →
  422, path traversal → 404, absurd policy → 422; unhandled exceptions now
  return a clean `500 INTERNAL_ERROR` envelope (no stack/internals leaked),
  and bodies over 10 MB are rejected with 413 before routing.
- **Frontend resilience:** stale saved run ids are forgotten on 404 instead
  of failing restore on every load; `npm run dev:clean` for the known
  `.next` corruption footgun.
- **Flake fixed by hardening:** the investigation test picked "the first
  run" and broke when a PASS run was inserted first in some orderings —
  it now selects a FAIL run explicitly (investigation is FAIL-only by rule).
- Results: backend **158 passed** (full suite, ~3 min), Playwright **5/5**,
  ruff/format/lint clean. Services healthy.

## Full English + i18n (2026-11-02, user decision: project is English-first)

- The whole web UI is now i18n: `LocaleProvider` + dictionary
  (`apps/web/lib/i18n.tsx`, `lib/locales/en.ts`; Turkish source strings are
  keys, missing entries fall back visibly). **Default locale: English**;
  TR/EN switcher in the titlebar, persisted in localStorage.
- Everything translated: chrome/tabs/status/help, scenario & robot panels,
  verdict cards (reason labels EN), investigation, fix sliders, gates,
  evidence/history, replay/timeline, report card (incl. backend scenario
  titles via `SCENARIO_TEXT_EN`, difficulty/category maps, dates),
  fleet/trend/import, admin, local policy, map import, canvas labels.
- The battery Markdown report is bilingual: `GET .../report.md?lang=en`
  (frontend follows the selected locale; default stays `tr` for API compat,
  covered by a new test).
- Verified: Playwright suite updated to English + a language-switch test —
  **7 passed**; browser proof both directions (EN default → TR switch).
  Backend battery/library/robot suites still green. (The stale copy in the
  TR note of the battery report that claimed no approval exists was also
  corrected: VERIFIED was earned in the meantime.)

## Execution State Details

- **Current phase:** PHASE 12 (hardening; Phases 07/10/12 partially open, see below)
- **Last verified checkpoint:** Full suite `58 passed`, ruff format+lint clean, live AI both endpoints `LIVE_META`, 7/7 evidence verifications (incl. candidate telemetry)
- **Live services (running):** backend `http://127.0.0.1:8000` (no-reload), worker (heartbeat fresh), frontend `http://localhost:3000`. UI flow proven in real browser tab: 359-frame baseline replay, measured investigate (tick 358), live verify → REJECTED, dual replay `BASE 359 / CAND 1340`.
- **Measured artifacts (repo-root `artifacts/`, DB `artifacts/robowitness.sqlite3`):**
  - baseline runs (incl. `run-904791dba73e` for v4): FAIL `[MIN_CLEARANCE_VIOLATION, COLLISION, GOAL_NOT_REACHED]` at tick 358, bit-identical across all law versions (+ UI-triggered runs)
  - `verif-90bfa84ad648` (candidate-final-v3 + avoidance law, frozen v4 HLD4-*): REJECTED **18/20** (HLD4-008, HLD4-016); gates 1,2,4,5 PASS; package verifies
  - `verif-38f767c1462f` (UI flow, offline patch): REJECTED, WITH sealed candidate replay (1340 frames)
  - `verif-1d13f3b0d992` (candidate-final-v1): REJECTED 17/20, WITH sealed candidate replay
  - baseline run `run-697c157aee28`: FAIL `[MIN_CLEARANCE_VIOLATION, COLLISION, GOAL_NOT_REACHED]`
  - `verif-19161efb3b2c` (candidate-final-v1 0.60/1.00/0.20/4.0/1.00): REJECTED — GATE_3 17/20 (HLD2-005 TIMEOUT; HLD2-006/017 COLLISION); gates 1,2,4,5 PASS
  - `verif-61f504916d9e` (candidate-B-v1 0.55/0.90/0.15/3.5/0.80): REJECTED — GATE_3 17/20 (HLD2-004/006/017); gates 1,2,4,5 PASS
  - `verif-c15a43a8b39a` (over-cautious): REJECTED — gates 2,3,4 FAIL (measured)
- **Open issues / honest gaps:**
  1. Path B CLOSED: `verif-6b2bfd8e0501` is `VERIFIED_IN_SIMULATION` on the pre-registered v6 set (20/20, MPC-lite, opt-in `RW_CANDIDATE_LAW=mpc`). Remaining gap is physical-world validation, not simulation verification; default law stays `shared`.
  2. Full-stack live flow re-verified after redesign: new baseline clears stale verification (no ghost pairs); NEW `GET /api/verifications` + history picker restores any past verification explicitly (`verif-58fc387d` → BASE 359 / CAND 1333, zero console errors).
  3. Fresh-venv install: PASS 2026-10-30 — clean venv `C:\Temp\rw-venv-test`, `pip install -e backend[dev]` (after pyproject `packages.find` fix), pybullet 3.2.7 source-built, **51 passed** on newest deps. Live Meta UNVERIFIED (endpoint+model unknown; provided key NOT used — no invented URLs).
- **Decisions/deviations:**
  - Single shared navigation law for baseline + candidate (blueprint §4.3: only 5 numeric params differ). Avoidance gain fixed at 2.0 (documented constant, not a 6th knob).
  - Holdout v1 → dev, v2 → eval (17/20, archived), v3 → eval (17/20, archived); each VERIFIED attempt uses a set the candidate never saw.
  - Artifact/DB paths anchored to repo root (were CWD-dependent; migrated + DB prefixes fixed + re-verified).
  - `requirements.lock` + `pyproject` updated to actually-tested versions; dead `asyncio_mode` setting removed.
  - Frontend: added `eslint-config-next@14.2.5` + `.eslintrc.json` (was unconfigured, `next lint` prompted interactively).
- **Next executable action:** Meta anahtarı için base URL + model ID iste (kullanıcı söz verdi, soru dialogu kapatıldı — chatten yazması bekleniyor) → Phase 05 canlı çağrı; plan kapanışı ve push.

## i18n Leak Audit (2026-11-02, user report: “Robotun yolu” still Turkish)

Systematic check: every `t("...")` key in `apps/web` vs the EN dictionary,
plus unwrapped user-facing strings. Found and fixed: the reported legend
key (`Robotun yolu` → `Robot path`), 3 more missing keys (`Testler
çalışıyor…`, `Yeni Robot Ekle`, lowercase `Çevrimdışı yedek`), 20 status/
badge/profile/robot message keys used only through dynamic lookups, and a
dozen unwrapped error/notice strings (RobotPanel, PolicyProfiles, page
fallback, JWT placeholder). Dynamic scenario titles were already covered
(`SCENARIO_TEXT_EN` incl. ultra + crowd). New Playwright guard asserts the
EN-mode body text contains zero Turkish characters (hidden tabs included) —
**8/8 e2e passed**. Note: an interim e2e failure in this session was a
stale dev server after running `next build` alongside `next dev` (known
`.next` corruption footgun, recovered with `dev:clean`), not an i18n
regression.

## Docs Sync + Logo (2026-11-02, user: “push atmadan önce bütün dosyaları güncelle”)

- **Logo:** new `docs/assets/logo.svg` (RW monogram + verification check on
  dark blueprint grid, recreated from the approved mark) + `apps/web/public/rw-mark.svg`
  used in the app titlebar and as favicon; README shows the logo above the title.
- **Fresh full verification for this push:** backend **159/159** (~4.5 dk, idle machine),
  web typecheck + build + `test:e2e` **8/8**, ruff clean. (An earlier in-session full run
  showed 6 failures under concurrent build+browser load; isolated re-run is green —
  recorded as load flake, not product regression.)
- **Docs brought current:** README (159 badge, 11-scenario battery, 6-tab English-first UI,
  four — not five — eval rejections), HACKATHON_SUBMISSION (same corrections + EN labels),
  RELEASE_1.0.0 (159 counts, E2E row, English-UI + 20/20 notes), ENTERPRISE (Path B closed,
  English UI names), CONTRACTS (candidate-law selector, 16-sample tracks, occlusion/beam,
  full 40-row endpoint table), EVIDENCE_FORMAT (battery report cards are generated, not sealed),
  DEMO_GUIDE (Path B CLOSED, English UI flow), Makefile (`test-frontend`/`test-e2e`/`coverage`),
  `.env.example` (JWT/OIDC, rate limit, webhook, worker, lease vars), requirements.lock header.
