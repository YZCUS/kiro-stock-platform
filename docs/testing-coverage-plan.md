# Testing Coverage Improvement Plan

## Current Baseline

Last verified locally on 2026-04-30.

- Backend: `192 passed`, product code coverage `29%`.
- Frontend: `126 passed`, statement coverage `24.87%`, branch coverage `13.65%`, function coverage `19.08%`, line coverage `24.93%`.
- E2E: `6 passed` on Chromium.
- Type check: frontend `tsc --noEmit` passed.
- Lint: frontend lint passed with existing warnings.

## Coverage Commands

```bash
make backend-coverage
make frontend-coverage
make test-coverage
make e2e
```

Direct commands used for the baseline:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests \
  --cov=backend/api --cov=backend/app --cov=backend/core \
  --cov=backend/domain --cov=backend/infrastructure

cd frontend && npm test -- --runInBand --coverage
cd frontend && npm run type-check
cd frontend && npm run test:e2e -- --project=chromium
```

## Phase 1: Stabilize Existing Tests

- Keep frontend global thresholds at the current passing baseline: statements `24`, branches `13`, functions `19`, lines `24`.
- Keep backend coverage reporting scoped to product code: `backend/api`, `backend/app`, `backend/core`, `backend/domain`, and `backend/infrastructure`.
- Remove or rewrite tests that only assert mocks were called without checking endpoint shape, payload mapping, validation, or rendered behavior.

## Phase 2: Raise Backend Confidence

- Add API route tests for auth, stock lists, portfolio, stock management, and strategies.
- Add repository tests for stock, price history, and technical indicator persistence with a test database.
- Add service tests for data validation, data collection retry behavior, strategy subscriptions, and strategy signal generation.
- Add trading tests for order intent lifecycle, broker adapter errors, read-only/live mode guardrails, and risk decision metadata.

## Phase 3: Raise Frontend Confidence

- Add tests for portfolio transaction flows, stock list CRUD flows, strategy subscription UI, and validation hooks.
- Prefer tests that render user workflows with React Testing Library over tests that only snapshot static markup.
- Expand Playwright coverage to authenticated portfolio/watchlist flows and backend error states.

## Phase 4: Increase Gates Gradually

- After each phase, raise thresholds only to levels proven by CI.
- Suggested next targets: frontend statements `30%`, backend product coverage `35%`.
- Long-term targets after core workflows are covered: backend `60%+`, frontend `50%+`, and E2E coverage for login, portfolio, watchlist, and dashboard.
