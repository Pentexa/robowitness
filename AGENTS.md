# RoboWitness coding-agent instructions

This repository is governed by `ROBOWITNESS_AGENT_EXECUTION_BLUEPRINT.md`. Read it completely before making changes. This document is a short entry point, not a replacement for the blueprint.

When the user says **START**, **BAŞLA**, **BEGIN**, **IMPLEMENT**, or **CONTINUE**, begin or resume **real source-code implementation immediately** in the current repository. Do not return a new plan or ask for separate approval for individual phases.

1. Inspect existing code/manifests and preserve prior functioning work.
2. Create/update `docs/IMPLEMENTATION_STATUS.md` with actual phase status, commands, results, and next executable action.
3. Implement blueprint **PHASE 01**, run its exit-gate checks, fix failing checks, log actual results; continue **PHASE 02 through PHASE 12** in order within the active session.
4. Resume from the earliest unverified gate after any interruption; never claim unattended work beyond the active session.
5. Do not fake telemetry, outcomes, AI calls, tests, evidence, holdout coverage, or real-world safety. Do not execute AI-generated code. Keep only one editing/build lane for shared files.
6. Missing live Meta credentials are not a blocker: complete the explicit offline reference flow and mark live connectivity unverified.
7. Report honestly what passed, what failed/was not run, reproducible commands, artifacts, and remaining blockers.

If the repo already contains an `AGENTS.md`, merge these instructions only when compatible with existing higher-priority instructions. Do not overwrite existing instructions or user work.
