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
- Live Meta AI integration (Muse Spark via api.meta.ai) generates new test
  scenarios and investigates failures from measured tick-level evidence;
  an offline reference mode keeps everything runnable without a key.
- Product surface: robot catalog (brand/model/specs, custom robots),
  21-scenario exam battery (including 5 ultra-hard and 5 crowd cases) with report cards,
  battery comparison/trends,
  fleets, policy profiles, your own Python policy (subprocess, opt-in),
  real-drive log judging, your own map → scenario, ROS 2 passive recorder.
- Enterprise layer: API keys/JWT/OIDC, roles, workspaces, audit trail,
  Prometheus, webhooks, scheduled batteries, idempotency, backups, CI gate,
  Docker Compose.

## The story judges should remember
For five consecutive frozen holdout sets, good-looking AI-era fixes scored
17/20, 17/20, 18/20, 18/20, 18/20 - and RoboWitness REJECTED them all, sealing the
evidence each time. We published the protocol, pre-registered a new
candidate (MPC-lite receding-horizon planner) BEFORE generating a fresh
set, and on that single shot it went 20/20: `verif-6b2bfd8e0501` —
**VERIFIED_IN_SIMULATION**, the first in project history. An over-cautious
control candidate was still rejected in the same run. The system does not
manufacture success; it makes success mean something.

## How we built it
FastAPI + SQLite atomic job worker + PyBullet DIRECT simulation, Next.js
dashboard (Turkish UI designed for non-experts), Pydantic contracts,
SHA-256 evidence packages with an independent verifier. 138 backend tests
pass, including in a fresh venv; Docker images built and run-verified.
Controller research (shared law → pass-behind/stateful/waypoint/MPC) was
run under a strict protocol: develop only on burned sets, pre-register,
single-shot on a fresh frozen set, publish the result either way.

## Try it in one minute (judges)
```powershell
python scripts\run_hackathon_demo.py   # ~5 s, offline-safe, exit 0
```
Then optionally: backend (`uvicorn app.main:app --port 8000`) + worker
(`python -m app.jobs.worker`) + web (`npm run dev`) → http://localhost:3000
→ Test tab → *Robotu Çalıştır*; Karne tab → *Bataryayı Çalıştır*.
With a Meta key in `.env` (`RW_AI_MODE=live`), scenario generation and
failure investigation go live via Muse Spark.

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

## 3-minute demo script
- **0:00–0:30** Problem: "AI fixed my robot" is self-graded homework. Show
  the baseline robot crash (tick 358, 0.0016 m) — deterministic, reproducible.
- **0:30–1:10** Click *İncele*: the investigation cites the measured tick
  and clearance from recorded telemetry; the AI only proposes a patch.
- **1:10–1:50** Show the verdict history: four frozen sets, four rejections
  (17–18/20). "We could have lowered the bar. The bar is the product."
- **1:50–2:40** The pre-registered MPC candidate: 20/20 on a set generated
  after registration → VERIFIED; re-verify the sealed package live
  (`scripts/verify_evidence.py`) — hashes match, byte by byte.
- **2:40–3:00** Karne tab: one click examines any catalog/custom robot
  across 11 scenarios and prints a report card. Close on the invariant:
  *The AI proposes. The oracle decides. The evidence proves.*

## Accomplishments we are proud of
- First honestly-earned VERIFIED after five documented rejections.
- Evidence that survives a second look: independent seal verification.
- Near-miss transparency: "reached the goal but unsafe" is explained in
  numbers, not hidden behind a red FAIL.
- A non-expert Turkish UI over a research-grade verification core.

## What we learned
Latency (350–400 ms) plus a strict stuck rule is a brutal teacher: four
controller families plateaued at 77/80 burned cases, and only receding
-horizon planning cleared it. Also: a demo that can say NO is worth more
than one that always says YES.

## What's next
MPC as an explicitly-selectable verified configuration is only the start:
live OIDC with a real IdP, a real ROS 2 robot on the recorder, beam-level
LiDAR fidelity, and a public leaderboard of sealed candidate exams.
