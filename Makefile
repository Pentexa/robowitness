.PHONY: help install test test-backend test-frontend dev-backend dev-worker dev-web run-offline-demo

help:
	@echo "RoboWitness Architecture & Run Commands:"
	@echo "  make install        - Install backend and frontend dependencies"
	@echo "  make dev-backend    - Run FastAPI backend on port 8000"
	@echo "  make dev-worker     - Run local jobs worker process"
	@echo "  make dev-web        - Run Next.js web application on port 3000"
	@echo "  make test-backend   - Run backend unit and integration tests"
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
	cd backend && pytest -v

run-offline-demo:
	python scripts/run_offline_demo.py
