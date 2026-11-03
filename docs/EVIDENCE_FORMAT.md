# RoboWitness Evidence Package Specification

This specification describes the recorded evidence files and integrity rules used by RoboWitness.
Battery report cards (`GET /api/batteries/{id}/report.md`, `?lang=tr|en`)
are *not* sealed evidence: they are generated summaries over individually
sealed runs, each row tracing to a `run_id` whose own package verifies.

## 1. Directory Structure

```text
artifacts/
├── runs/
│   └── <run_id>/
│       ├── scenario.json
│       ├── policy.json
│       ├── manifest.json
│       ├── telemetry.jsonl
│       ├── metrics.json
│       ├── events.jsonl
│       └── hashes.json
└── verifications/
    └── <verification_id>/
        ├── manifest.json
        ├── investigation.json
        ├── comparison.json
        ├── holdout_results.json
        ├── regression_results.json
        ├── report.md
        ├── telemetry_candidate.jsonl   # optional: sealed paired-candidate frames
        └── hashes.json                 # (for verifications sealed after candidate replay;
                                        #  older packages verify without it — required list unchanged)
```

## 2. Integrity & Cryptographic Sealing
- Every completed artifact file is hashed using SHA-256 (`lowercase hex`).
- `hashes.json` maps relative file paths to their SHA-256 digest.
- `hashes.json` itself is never included in its own checksum mapping (no circular dependency).
- The verifier independently recalculates digests; any missing file or mismatched hash results in `ARTIFACT_INTEGRITY_FAILURE` and status `INCONCLUSIVE`.

## 3. Human-Readable Report (`report.md`)
Each verification package generates an evidence report containing:
- Test scope and software-only simulation disclaimer.
- Baseline failure evidence (tick, clearance, contact, reason).
- Candidate policy parameter diff and paired comparative metrics.
- 20 holdouts results (passed/total, individual seeds).
- Critical regression suite outcomes.
- Independent oracle verdict (`VERIFIED_IN_SIMULATION`, `REJECTED`, or `INCONCLUSIVE`).
- SHA-256 integrity verification instructions.
