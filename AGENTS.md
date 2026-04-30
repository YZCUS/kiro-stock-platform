# Repository Guidelines

## Project Structure & Module Organization

This stock analysis platform is split into backend, frontend, and workflow layers. Backend code lives in `backend/`: FastAPI startup and DI in `app/`, routes in `api/routers/v1/`, business logic in `domain/services/`, repository interfaces in `domain/repositories/`, adapters in `infrastructure/`, models in `domain/models/`, and tests in `backend/tests/`. Frontend code lives in `frontend/src/`, with App Router pages in `app/`, UI in `components/`, API clients in `services/`, state in `store/`, and E2E tests in `frontend/tests/e2e/`. Airflow DAGs and plugins live in `airflow/`; deployment files include `docker-compose.yml`, `nginx/`, and `scripts/`.

## Build, Test, and Development Commands

- `make dev-setup`: build images, start services, initialize and seed the database.
- `make up` / `make down` / `make logs`: manage the local Docker stack.
- `make test`: run backend pytest tests and frontend Jest tests.
- `make lint` / `make format`: run backend and frontend linting or formatting.
- `cd backend && uvicorn app.main:app --reload`: run the API locally.
- `cd frontend && npm run dev`: run Next.js on `localhost:3000`.
- `cd frontend && npm run build`: build the production frontend.

## Coding Style & Naming Conventions

Use 4-space indentation for Python, formatted with Black and checked with Flake8. Keep FastAPI routers thin: HTTP concerns stay in `api/`, business rules in `domain/`, and external systems in `infrastructure/`. Register services through `app/dependencies.py`. In TypeScript, use PascalCase for components, `use*` for hooks, camelCase for variables/functions, and TailwindCSS plus shadcn/ui patterns for shared UI.

## Testing Guidelines

Backend tests use pytest. Place unit tests in `backend/tests/unit/`, API or database integration tests in `backend/tests/integration/`, and full workflows in `backend/tests/e2e/`. Name Python files `test_*.py` and functions `test_*`. Frontend tests use Jest/React Testing Library; Playwright E2E tests run with `npm run test:e2e`. Update tests when changing domain services, API contracts, authentication, portfolio logic, or chart workflows.

## Commit & Pull Request Guidelines

Recent history uses short Conventional Commit style subjects such as `fix: ...`; follow that pattern with imperative messages (`feat: add portfolio summary filter`, `fix: resolve Docker build dependency`). Pull requests should include a description, verification commands, linked issues, screenshots for UI changes, and notes for migrations or environment changes.

## Security & Configuration Tips

Do not commit secrets, JWT keys, database URLs, or API credentials. Keep environment-specific values in local `.env` files or deployment configuration. When changing schema, add Alembic migrations and document required database steps in the PR.
