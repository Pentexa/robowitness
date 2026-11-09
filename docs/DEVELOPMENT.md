# Development Guide

Workflows, CI/CD, and contributing for RoboWitness. Pipelines report measured
results only — a green check means the commands actually ran and passed.

## Workflows

| Workflow | File | Triggers | Purpose |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | push/PR to `main`, manual | Test, lint, build, live-stack E2E, Docker smoke |
| Release | `.github/workflows/release.yml` | tags `v*`, manual | Version gate → test gate → GHCR images → GitHub Release |
| Security | `.github/workflows/security.yml` | push, PR, weekly | CodeQL, dependency review + audits |
| Dependabot | `.github/dependabot.yml` | weekly | Grouped dependency-update PRs |

- CI runs on Ubuntu with the offline reference configuration
  (`RW_AI_MODE=offline`, `RW_CANDIDATE_LAW=shared`); no secrets and no live AI
  calls. Jobs: backend (ruff + pytest with coverage), frontend (lint,
  typecheck, build), live-stack E2E (three real processes + Playwright),
  Docker compose smoke, and a required aggregate gate.
- Releases are tag-driven: the tag, `backend/pyproject.toml`, and
  `apps/web/package.json` versions must agree; images are published to GHCR
  with SBOM/provenance attestations; release notes come from
  `docs/RELEASE_<version>.md` when present.
- Security: CodeQL is the gating check; pip-audit/npm audit are informational
  and triaged via Dependabot.
- Branch protection (recommended): require the `CI · required gate` check and
  CodeQL, require PR, disallow bypass.

## Local Checks

```bash
# Backend (from backend/)
ruff format --check app tests && ruff check --select E,F app tests && pytest -q

# Frontend (from apps/web/)
npm ci && npm run lint && npm run typecheck && npm run build

# Live stack + E2E: start backend, worker, web, then
python scripts/e2e_live_stack.py && cd apps/web && npm run test:e2e

# Docker smoke
docker compose up --build -d && curl -s http://127.0.0.1:8000/api/health
docker compose down -v
```

## Contributing

Issues and pull requests are welcome. Before opening a PR:

1. Run the backend tests and frontend checks above.
2. Keep the invariant intact: never let a policy see ground truth, never let
   the proposer grade itself, never manufacture a verdict.
3. Add measured evidence for behavioral claims — commands, IDs, and
   artifacts, not adjectives.
