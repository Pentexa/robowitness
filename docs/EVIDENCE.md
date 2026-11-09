# Evidence Package Specification

Every completed run and verification produces a sealed evidence package.
Battery report cards (`GET /api/batteries/{id}/report.md`) are generated
summaries, not sealed evidence — each row traces to a `run_id` whose own
package verifies.

## Directory Structure

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
        └── hashes.json
```

## Integrity & Sealing

- Every completed artifact file is hashed with SHA-256 (lowercase hex).
- `hashes.json` maps relative file paths to their digests; it never includes
  its own checksum.
- The verifier independently recalculates all digests. A missing file or any
  mismatched hash results in `ARTIFACT_INTEGRITY_FAILURE` and an
  `INCONCLUSIVE` verdict — the pipeline prefers "I don't know" over trust me.

## Package Contents (`report.md`)

Each verification package includes a readable report with: test scope and a
software-only disclaimer, baseline failure evidence (tick, clearance, contact,
reason), candidate parameter diff and paired metrics, 20 holdout results by
seed, regression outcomes, the oracle verdict, and integrity instructions.

## Verify Any Package

```bash
python scripts/verify_evidence.py artifacts/verifications/<verification_id>
```

The dashboard's Evidence Inspector (Result tab) re-verifies uploaded ZIPs the
same way, independently.
