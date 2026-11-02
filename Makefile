.PHONY: help install test test-backend test-frontend test-e2e coverage fmt lint-backend dev-backend dev-worker dev-web run-offline-demo

help:
	@echo "RoboWitness Architecture & Run Commands:"
	@echo "  make install        - Install backend and frontend dependencies"
	@echo "  make dev-backend    - Run FastAPI backend on port 8000"
	@echo "  make dev-worker     - Run local jobs worker process"
	@echo "  make dev-web        - Run Next.js web application on port 3000"
	@echo "  make test-backend   - Run backend unit and integration tests"
	@echo "  make test-frontend  - Run web lint + typecheck + production build"
	@echo "  make test-e2e       - Run Playwright browser E2E (needs backend+worker+web running)"
	@echo "  make coverage       - Run backend tests with coverage report"
	@echo "  make fmt            - Format backend with ruff"
	@echo "  make lint-backend   - Ruff format-check + lint (E,F) for backend"
	@echo "  make run-offline-demo - Run end-to-end offline reference flow"

install:
	cd backend && pip install -e ".[dev]"
	cd apps/web && npm install

dev-backend:
	cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

dev-worker:
	cd backend && python -m app.jobs.worker

dev-web:
	cd apps/web && npm run dev

test-backend:
	cd backend && pytest

test-frontend:
	cd apps/web && npm run lint && npm run typecheck && npm run build

test-e2e:
	cd apps/web && npm run test:e2e

coverage:
	cd backend && pytest --cov=app --cov-report=term  # needs: pip install pytest-cov

fmt:
	ruff format backend/app backend/tests

lint-backend:
	ruff format --check backend/app backend/tests
	ruff check --select E,F backend/

run-offline-demo:
	python scripts/run_offline_demo.py
