# RoboWitness CI/CD

This document describes the continuous integration and delivery setup under
`.github/`. Design rule inherited from the product itself: **pipelines report
measured results only** — a green check means the commands below actually ran
and passed on that commit, and a missing capability fails the job instead of
being mocked green.

## 1. Workflows at a glance

| Workflow | File | Triggers | Purpose |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | push to `main`, PRs to `main`, manual | Test, lint, build, live-stack E2E, Docker smoke |
| Release | `.github/workflows/release.yml` | tags `v*`, manual (version input) | Version gate → test gate → GHCR images → GitHub Release |
| Security | `.github/workflows/security.yml` | push, PRs, Mondays 06:00 UTC, manual | CodeQL, dependency review, dependency audits |
| Dependabot | `.github/dependabot.yml` | Mondays 07:00 UTC | Grouped dependency-update PRs (pip, npm, Actions, Docker) |

Status badges in `README.md` point at the CI, Release, and Security workflows.

## 2. CI workflow — jobs

All jobs run on `ubuntu-latest` with Python 3.11 and Node 20 (same majors as
`Dockerfile.backend` / `Dockerfile.web`). The environment is pinned to the
offline reference configuration (`RW_AI_MODE=offline`,
`RW_ALLOW_LOCAL_POLICY=off`, `RW_CANDIDATE_LAW=shared`, `RW_SENSOR_MODEL=legacy`),
so CI measures exactly the configuration every frozen result in this
repository was produced with (see `docs/VERIFICATION_PROTOCOL.md`). No secrets are used and no live Meta/SAM call
can happen: the backend test fixture additionally blanks all credentials.

| Job | What runs | Failure means |
|---|---|---|
| **Backend** | `ruff format --check`, `ruff check --select E,F`, full `pytest` with coverage + JUnit XML (uploaded as artifacts) | Style drift, lint regression, or any of the backend tests failing |
| **Frontend** | `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` | Lint/type errors or a broken production build |
| **E2E** (needs Backend + Frontend) | Installs backend + web, builds web, starts backend + worker + web, waits for `/api/health` with `worker_active=true`, runs `scripts/e2e_live_stack.py`, then Playwright `npm run test:e2e` | A broken live journey (HTTP or browser level) |
| **Docker** | Builds both images (BuildKit + GHA layer cache), `docker compose up -d --no-build`, health + web-200 smoke, logs on failure, `down -v` | Broken image build or compose wiring |
| **CI · required gate** | Aggregates the four jobs above (`needs` + explicit result check) | Any required job did not succeed |

Notes:

- Superseded runs on the same ref are cancelled automatically
  (`concurrency`), except releases, which are never cancelled.
- The E2E job mirrors a developer machine: three real processes over real
  HTTP. Playwright traces and stack logs (`ci-logs/`) are uploaded on failure.
- The sealed champion evidence under `artifacts/` is gitignored, so
  `scripts/run_hackathon_demo.py` is **not** part of CI — it would have
  nothing to re-verify on a bare clone. It stays a local judge-demo script;
  CI covers the same code paths through the test suites and live-stack E2E.
- `scripts/ci_battery_gate.py` is likewise a consumer-side gate for external
  pipelines (bring your own thresholds and running stack); the in-repo CI
  does not impose a pass-rate on the baseline policy, because the baseline is
  *expected* to fail most scenarios.

## 3. Release workflow (CD)

Pushing a tag such as `v1.0.1` (or dispatching manually with a version input)
runs:

1. **Version gate** — the tag, `backend/pyproject.toml`, and
   `apps/web/package.json` versions must agree exactly, or the release stops
   before anything is built.
2. **Test gate** — full backend suite (lint + pytest) and frontend
   lint/typecheck/build re-run on the tagged commit.
3. **Image publishing** — `ghcr.io/<owner>/<repo>-backend` and
   `ghcr.io/<owner>/<repo>-web` are built and pushed with tags
   `<version>`, `latest`, and `sha-<commit>`, including SBOM and provenance
   attestations. Authentication uses the workflow's `GITHUB_TOKEN`
   (`packages: write`); no personal tokens are stored.
4. **GitHub Release** — created from `docs/RELEASE_<version>.md` when that
   file exists (fallback: a generated note), with the image references
   appended and GitHub's auto-generated changelog enabled.

Images are never published from untagged commits, and the release job cannot
be cancelled mid-flight.

## 4. Security workflow

- **CodeQL** analyzes Python and JavaScript/TypeScript on every push/PR and
  weekly; findings land in the repository's Security tab.
- **Dependency Review** (PRs only) fails a PR that introduces a
  high-severity vulnerable dependency and comments the summary on failure.
- **Dependency Audit** runs `pip-audit` and `npm audit`, uploading JSON
  reports as artifacts. It is intentionally informational
  (`continue-on-error`): audit findings are triaged manually and fixed via
  Dependabot PRs, rather than turning `main` red the day a new CVE is
  published against a pinned transitive dependency. CodeQL remains the
  gating security check.

## 5. Dependabot

Weekly grouped PRs for pip (`backend/`), npm (`apps/web/`), GitHub Actions,
and Docker base images. Minor/patch updates are grouped; majors arrive
individually. All Dependabot PRs must pass the CI workflow before merge —
the same rule as human PRs (see `.github/pull_request_template.md`).

## 6. Branch protection (recommended settings)

CI cannot enforce itself; configure once under
**Settings → Branches → Add rule** for `main`:

- Require a pull request before merging (1 approval).
- Require status checks: **CI · required gate**, **CodeQL · python**,
  **CodeQL · javascript-typescript**.
- Require branches to be up to date before merging.
- Do not allow bypassing the above settings.

With that rule, the single `CI · required gate` check is the merge gate;
individual job names remain visible for diagnosis.

## 7. Running the same checks locally

```powershell
# Backend (from backend/)
ruff format --check app tests; ruff check --select E,F app tests; pytest -q

# Frontend (from apps/web/)
npm ci; npm run lint; npm run typecheck; npm run build

# Live stack + E2E: start backend, worker, web (three terminals), then
python scripts/e2e_live_stack.py
cd apps/web; npm run test:e2e

# Docker smoke
docker compose up --build -d; curl http://127.0.0.1:8000/api/health
docker compose down -v
```

## 8. Honest limits

- CI runs on GitHub-hosted Ubuntu runners; the Windows/MSVC PyBullet source
  build path used on the maintainer's machine is covered by
  `scripts/bootstrap.ps1` locally, not by CI (Linux uses the published
  manylinux wheel).
- No live Meta AI or SAM 3.1 calls run in CI (no secrets, no spend). Those
  paths are covered by recorded-transport tests; live proof stays with the
  paid smoke scripts (`scripts/sam_live_smoke.py`,
  `scripts/sam_browser_smoke.cjs`, `scripts/live_smoke.py`).
- Load/performance testing is not part of CI; no throughput numbers are
  claimed anywhere in this repository.
