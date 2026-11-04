## What changed

<!-- One or two sentences. Link issues if any. -->

## How it was verified

<!-- Measured results only — commands run and their outcomes. No claims
     without evidence; if something could not be run, say so explicitly. -->

- [ ] Backend: `ruff format --check` + `ruff check --select E,F` + `pytest` (in `backend/`)
- [ ] Frontend: `npm run lint` + `npm run typecheck` + `npm run build` (in `apps/web/`)
- [ ] E2E (if UI/API behavior changed): live stack + `npm run test:e2e`
- [ ] Docker (if packaging changed): `docker compose up --build` smoke

## Project rules checklist

- [ ] No fabricated telemetry, outcomes, AI responses, or verdicts; missing
      capabilities fail honestly (blocked/error states, not invented data)
- [ ] AI-generated code is never executed by the product; local policies stay
      opt-in (`RW_ALLOW_LOCAL_POLICY`) and default-off
- [ ] Frozen holdout sets untouched; default candidate law `shared` and sensor
      model `legacy` preserved (backward-compatible measurements)
- [ ] Docs updated (`README.md` and the relevant `docs/*.md`; contracts
      too if API/schemas changed)
- [ ] No secrets, API keys, or `artifacts/` contents committed
