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
| PHASE 09 | PASS (gates honest; Path B UNMET) | Frozen 20 holdouts, regressions, sealed verdict | `run_final_evaluation.py` + `test_verification.py` | v1 set used for dev tuning → archived as `manifest_v1_dev.json`; fresh frozen v2 set generated (`generate_holdout_v2.py`, 20/20 valid). Candidate-final-v1: 17/20 → REJECTED. Candidate-B-v1: 17/20 → REJECTED. Over-cautious: REJECTED (gates 2,3,4). No VERIFIED manufactured. |
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
  1. Path B UNMET after 4 frozen eval sets + 60-case grids (best 59/60 twice: F1 and k07 0.65/1.0/1.0/4.0; HLD2-017 fails under every law/param — max-difficulty corner: 0.5 m/s + 350 ms + noise). VERIFIED needs a richer controller family or narrower holdout ODD.
  2. Full-stack live flow re-verified after redesign: new baseline clears stale verification (no ghost pairs); NEW `GET /api/verifications` + history picker restores any past verification explicitly (`verif-58fc387d` → BASE 359 / CAND 1333, zero console errors).
  3. Fresh-venv install: PASS 2026-10-30 — clean venv `C:\Temp\rw-venv-test`, `pip install -e backend[dev]` (after pyproject `packages.find` fix), pybullet 3.2.7 source-built, **51 passed** on newest deps. Live Meta UNVERIFIED (endpoint+model unknown; provided key NOT used — no invented URLs).
- **Decisions/deviations:**
  - Single shared navigation law for baseline + candidate (blueprint §4.3: only 5 numeric params differ). Avoidance gain fixed at 2.0 (documented constant, not a 6th knob).
  - Holdout v1 → dev, v2 → eval (17/20, archived), v3 → eval (17/20, archived); each VERIFIED attempt uses a set the candidate never saw.
  - Artifact/DB paths anchored to repo root (were CWD-dependent; migrated + DB prefixes fixed + re-verified).
  - `requirements.lock` + `pyproject` updated to actually-tested versions; dead `asyncio_mode` setting removed.
  - Frontend: added `eslint-config-next@14.2.5` + `.eslintrc.json` (was unconfigured, `next lint` prompted interactively).
- **Next executable action:** Meta anahtarı için base URL + model ID iste (kullanıcı söz verdi, soru dialogu kapatıldı — chatten yazması bekleniyor) → Phase 05 canlı çağrı; plan kapanışı ve push.
