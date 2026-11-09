# Usage Guide

Start the three services first (see the README Quick Start): FastAPI backend
on :8000, the job worker, and the Next.js dashboard on :3000.

## Web Workflow

The dashboard walks you through the full loop:

```
Pick Scenario → Run Baseline → Replay Failure → Inspect → Review Fix
→ Test the Fix → Compare Runs → Inspect Verdict → Download Evidence ZIP
→ Report Card → Admin
```

## What to Try

1. **Run a failure** — Test tab, pick scenario `RW-REF-001` (moving obstacle,
   450 ms sensor latency), run the baseline. Telemetry and the oracle report
   `COLLISION` / `MIN_CLEARANCE_VIOLATION` with the exact failure tick.
2. **Inspect it** — Inspect tab shows a grounded analysis tied to the measured
   tick and clearance, ending in a proposed 5-parameter patch.
3. **Verify the fix** — Fix tab, adjust parameters or apply the AI suggestion,
   then submit for verification. Gates 1–5 run; the Result tab shows the
   verdict, paired replay, and a sealed evidence ZIP.
4. **Report Card** — one click runs the default 11-scenario battery for any
   catalog or custom robot and prints a per-scenario report card.
5. **Stress Test tab** — pick latency × noise chips; every heatmap cell is a
   real recorded run with its measured minimum clearance.
6. **Adversarial test** (Test tab) — the AI proposes ever-harder scenarios
   from measured failures; the oracle — never the AI — judges each run.
7. **Evidence Inspector** (Result tab) — download an evidence ZIP, re-upload
   it, and watch SHA-256 integrity recomputed independently.
8. **Portable HTML report** (Result tab) — one standalone file with gates,
   measured comparison, clearance chart, and evidence hashes; opens offline.
9. **Photo to scenario** (Test tab) — upload a still or capture a photo,
   detect objects, confirm scale + overhead view, place start/goal, preview
   and save a runnable scenario. Photos are not stored; only measured boxes
   and a source hash are.
10. **Real-log import** — upload a real drive as CSV or JSON; it is judged by
    the same oracle rules and labeled `REAL_LOG`.

## Viewing: 2D (canonical) and 3D (display only)

- The 2D canvas is the canonical evidence view (exact telemetry coordinates).
- The 3D view mirrors the same frames for visualization only; it never touches
  physics, the oracle, or evidence. Full 3D physics is out of scope.

## Terminal Demos

```bash
python scripts/run_offline_demo.py   # baseline fail / candidate test, ~seconds, no key
python scripts/run_demo.py           # full story incl. sealed evidence re-verification
python scripts/ros2_bridge.py        # passive recorder: listens to /odom and /scan only
```

Optional enterprise features (API keys, workspaces, audit, backups) are
documented in [`ENTERPRISE.md`](ENTERPRISE.md); with nothing configured
everything works in open local mode.
