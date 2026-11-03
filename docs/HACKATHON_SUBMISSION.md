# RoboWitness — Meta Global AI Developer Hackathon Submission

## One-liner
RoboWitness independently verifies AI-generated robotics policy fixes:
the AI proposes, the simulator executes, an independent oracle decides,
and SHA-256-sealed evidence proves it — including the failures.

## Inspiration
Every week someone posts "the AI fixed my robot." The model writes the fix
and then everyone trusts the same model's confidence. In robotics that
trust can bend hardware. We asked: what if an AI policy fix had to pass an
exam it cannot see, graded by a judge that never reads its reasoning?

## What it does
- Runs a candidate policy in a deterministic PyBullet world (60 Hz, seeded)
  where the policy only sees delayed (0–1000 ms) and noisy sensor data.
- An independent oracle judges true geometry: collision, minimum clearance,
  goal, timeout, stuck — PASS / FAIL / INCONCLUSIVE with machine reasons.
- Five gates: baseline-failure reproduction, paired comparison, 20 frozen
  holdout scenarios, critical regressions, cryptographic evidence sealing
  (independently re-verified before any VERIFIED verdict is published).
- Live Meta AI integration (Muse Spark 1.3 via api.meta.ai) generates new test
  scenarios and investigates failures from measured tick-level evidence;
  an offline reference mode keeps everything runnable without a key.
- Product surface: robot catalog (brand/model/specs, custom robots),
  11-scenario default exam battery (10 more scenarios in the library: 5 ultra-hard, 5 crowd) with report cards,
  battery comparison/trends,
  fleets, policy profiles, your own Python policy (subprocess, opt-in),
  real-drive log judging, your own map → scenario, ROS 2 passive recorder.
- Enterprise layer: API keys/JWT/OIDC, roles, workspaces, audit trail,
  Prometheus, webhooks, scheduled batteries, idempotency, backups, CI gate,
  Docker Compose.

## Where and how we used the three Meta models

| Model | Where we used it | Input and method | Contribution to RoboWitness |
|---|---|---|---|
| **[Muse Wonder](https://dev.meta.ai/models/muse-wonder)** | Development and coding workflow | Used as a coding assistant while developing RoboWitness, supporting implementation work through code suggestions and changes | Helped build and iterate on the application; changes enter the repository's review and automated-test workflow |
| **[Muse Spark 1.3](https://dev.meta.ai/models/muse-spark)** | Runtime scenario generation, failure investigation and fix proposals | The backend sends an objective or a summary of measured failure evidence to the Meta Model API's `/chat/completions`, with `RW_META_MODEL=muse-spark-1.3` | Returns a schema-validated scenario, or a failure hypothesis and a patch limited to five numeric controller parameters |
| **[SAM 3.1](https://dev.meta.ai/docs/sam/segmenting)** | Runtime camera/photo-to-scenario workflow | A still image plus a short object concept is sent to `/responses` with `model=sam-3.1`; the official SAM parser validates the returned boxes and masks | Detects objects for selection and preview; application code uses the user's floor dimensions to project selected boxes into static circular PyBullet obstacles |

### Muse Wonder — development-time coding assistance

We used Muse Wonder as a **development/coding assistant** while building
RoboWitness. This is its contribution to the engineering workflow: assistance
with implementing and iterating on source code. Resulting changes are checked
through the project's normal tests and review process. The application runtime
described below uses Muse Spark 1.3 and SAM 3.1; Muse Wonder's attribution is for
development assistance, as confirmed by the project author.

### Muse Spark 1.3 — runtime reasoning and structured proposals

- **Generate a scenario:** Test → **Generate with Meta AI** calls
  `POST /api/scenarios/generate`. The backend sends the requested objective and
  a JSON schema template to Muse Spark 1.3, then validates its answer as a
  `ScenarioSpec` before the scenario can be run.
- **Investigate a failure:** after an oracle-FAIL run, Inspect calls
  `POST /api/failures/{run_id}/investigate`. The application extracts recorded
  collision/minimum-clearance ticks, frame count and goal/collision measurements
  from the run's telemetry. The model receives this measured evidence summary
  and returns a testable hypothesis plus a proposed parameter patch.
- **Propose a fix:** the patch can contain only `max_speed_mps`,
  `safe_distance_m`, `reaction_margin_m`, `brake_gain`, and
  `obstacle_prediction_horizon_s`. The user can review/apply these values;
  the same independent verification pipeline evaluates the candidate.

Implementation: [MetaAdapter](../backend/app/ai/adapter.py),
[scenario route](../backend/app/api/routes_scenarios.py),
[measured-evidence investigation](../backend/app/api/routes_failures.py), and
[policy patch schema](../backend/app/schemas/policy.py).
Live text inference is configured server-side with `RW_AI_MODE=live`,
`RW_META_BASE_URL`, `RW_META_API_KEY` and `RW_META_MODEL=muse-spark-1.3`.
Valid live results are labeled `LIVE_META`; offline reference results are
explicitly labeled `OFFLINE_REFERENCE`.

### SAM 3.1 — runtime still-image perception

In Test → **Camera / Photo → SAM 3.1**, the user uploads a PNG/JPEG/WebP photo
or captures a single camera snapshot. **Detect with SAM 3.1** calls
`POST /api/scenarios/from-image/detect`. The backend sends the image and each
requested object concept to the actual SAM 3.1 API using the server-side Meta
key. The official `meta-sam-parser` validates segmentation boxes and masks,
and the UI displays the detected objects with confidence when supplied.

The user selects 1–8 obstacles, confirms an overhead/rectified floor view,
enters physical floor width/height and places start/goal points. Ordinary
application code projects the image boxes into enclosing static circles,
validates the resulting `ScenarioSpec`, and supports preview, workspace-scoped
save/reload, and **Save and run** through the existing PyBullet worker.
The scale comes from the user; depth and obstacle motion are not inferred.

Implementation: [camera/photo UI](../apps/web/components/ImageScenarioPanel.tsx),
[SAM adapter](../backend/app/ai/sam.py),
[image routes](../backend/app/api/routes_image_scenarios.py), and
[image-to-world conversion](../backend/app/maps/image_converter.py).

### What decides the result, and what we actually checked

PyBullet executes the scenario, the deterministic oracle evaluates measured
behavior, and the five-gate protocol plus evidence integrity determine the
verification verdict. Model suggestions do not assign `VERIFIED_IN_SIMULATION`.

- **Muse Wonder:** development-time use is confirmed by the author; this is
  engineering attribution, not an application inference test result.
- **Muse Spark 1.3:** live scenario-generation and grounded-investigation
  results are recorded in [implementation status](IMPLEMENTATION_STATUS.md).
  The documented ultra scenario demonstrates that even a live Meta fix whose
  paired test succeeds can be rejected by the holdout gate.
- **SAM 3.1:** actual-photo detection found two cats in the public COCO sample.
  A separate rendered, known-scale overhead calibration image exercised the
  full real SAM → preview/save → PyBullet → reload journey. Latest recorded
  run `run-1db85969c259`: 2 detected objects, 741 simulation ticks, goal reached,
  zero collisions, minimum clearance 0.4137 m. The two image checks have
  distinct scopes: real-photo segmentation and calibrated simulation input.

## The story judges should remember
For four consecutive frozen holdout sets, good-looking AI-era fixes scored
17/20, 17/20, 18/20, 18/20 — and RoboWitness REJECTED them all, sealing the
evidence each time. We published the protocol, pre-registered a new
candidate (MPC-lite receding-horizon planner) BEFORE generating a fresh
set, and on that single shot it went 20/20: `verif-6b2bfd8e0501` —
**VERIFIED_IN_SIMULATION**, the first in project history. An over-cautious
control candidate was still rejected in the same run. The system does not
manufacture success; it makes success mean something.

## How we built it

We used **Muse Wonder for development/coding assistance**, **Muse Spark 1.3
for runtime scenario generation and failure reasoning**, and **SAM 3.1 for
camera/photo segmentation**, as detailed above.

FastAPI + SQLite atomic job worker + PyBullet DIRECT simulation, Next.js
dashboard (English-first UI with Turkish switch, designed for non-experts), Pydantic contracts,
SHA-256 evidence packages with an independent verifier. 194 backend tests
(incl. 35 image/SAM cases) plus 18 Playwright E2E (incl. camera, photo,
scale gate); Docker images built and run-verified.
Controller research (shared law → pass-behind/stateful/waypoint/MPC) was
run under a strict protocol: develop only on burned sets, pre-register,
single-shot on a fresh frozen set, publish the result either way.

## Try it in one minute (judges)
```powershell
python scripts\run_hackathon_demo.py   # ~5 s, offline-safe, exit 0
```
Then optionally: backend (`uvicorn app.main:app --port 8000`) + worker
(`python -m app.jobs.worker`) + web (`npm run dev`) → http://localhost:3000
→ Test tab → *Run Robot*; Report Card tab → *Run the Battery*.
With a Meta key in `.env` (`RW_AI_MODE=live`), scenario generation and
failure investigation go live via Muse Spark 1.3 (`RW_META_MODEL=muse-spark-1.3`).

## The ultra-hard showcase (measured live, 2026-11-02)
Five ULTRA scenarios (`scenarios/ultra/`, in the library as "Ultra"):
900 ms latency wall, dual onslaught, double crossing, noise storm
(0.20 m), goal guardian. Measured with the frozen demo test
(`tests/unit/test_ultra_scenarios.py`): the baseline policy fails all
five; a Meta-style patch driven by the MPC candidate law passes all five.

Live on stage (real Meta call, not a recording): baseline crashed on
RW-ULTRA-002 (collision), Muse Spark investigated from recorded
telemetry (failure tick 283, provenance `LIVE_META`) and proposed its
patch. RoboWitness then examined *that* solution:
- Gate 2 (paired, same ultra scenario): **PASS** — Meta's fix really works there.
- Full exam: **REJECTED at 19/20** (`verif-e691c7dc3096`) — one stuck case
  (RW-HLD6-013) kept it from VERIFIED. Even a great Meta answer does not
  get a free pass; the pre-registered champion (`verif-6b2bfd8e0501`,
  20/20) is what earning it looks like.

## Crowd mode (when the judge asks "but what about people?")
Five crowd scenarios (pedestrian streams, a two-way corridor, goal
guards, a market square, 0.9 m/s runners at 500 ms latency) ship in the
library. The baseline fails all five. A crowd-tuned MPC variant
(closed-loop rollouts + prediction-uncertainty inflation) passes all
five — and live-verified the market scenario end-to-end
(`verif-b9ce2a55155e`, VERIFIED with the crowd configuration).
Frozen expectations: `tests/unit/test_crowd_scenarios.py`.

## Camera to scenario (Meta SAM 3.1, measured)

Upload a PNG/JPEG/WebP still or capture a camera photo in the Test tab and
click **Detect with SAM 3.1**: a real Meta Responses API request segments
your object concepts, and the measured boxes become static circular
obstacles in a saved, runnable scenario. The suite proves the whole chain
with a recorded SAM response (35 backend cases, 10 image/browser E2E incl. camera
cleanup, permission-denied fallback, retry/job failures and the scale/overhead gate); live
runs are covered by `scripts/sam_live_smoke.py` and the paid
`scripts/sam_browser_smoke.cjs` UI smoke, never by the default suite.

## 3-minute demo script
- **0:00–0:30** Problem: "AI fixed my robot" is self-graded homework. Show
  the baseline robot crash (tick 358, 0.0016 m) — deterministic, reproducible.
- **0:30–1:10** Click *Inspect*: the investigation cites the measured tick
  and clearance from recorded telemetry; the AI only proposes a patch.
- **1:10–1:50** Show the verdict history: four frozen sets, four rejections
  (17–18/20). "We could have lowered the bar. The bar is the product."
- **1:50–2:40** The pre-registered MPC candidate: 20/20 on a set generated
  after registration → VERIFIED; re-verify the sealed package live
  (`scripts/verify_evidence.py`) — hashes match, byte by byte.
- **2:40–3:00** Report Card tab: one click examines any catalog/custom robot
  across the default battery and prints a report card. Close on the invariant:
  *The AI proposes. The oracle decides. The evidence proves.*

## Accomplishments we are proud of
- First honestly-earned VERIFIED after four documented rejections.
- Evidence that survives a second look: independent seal verification.
- Near-miss transparency: "reached the goal but unsafe" is explained in
  numbers, not hidden behind a red FAIL.
- A non-expert English-first UI (Turkish switchable) over a research-grade verification core.

## What we learned
Latency (350–400 ms) plus a strict stuck rule is a brutal teacher: four
controller families plateaued at 77/80 burned cases, and only receding
-horizon planning cleared it. Also: a demo that can say NO is worth more
than one that always says YES.

## What's next
MPC as an explicitly-selectable verified configuration is only the start:
live OIDC with a real IdP, a real ROS 2 robot on the recorder, beam-level
LiDAR fidelity, and a public leaderboard of sealed candidate exams.
