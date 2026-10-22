BACKEND := backend
FRONTEND := frontend
PY := $(BACKEND)/.venv/bin

.PHONY: install install-backend install-frontend up down logs prod migrate seed openapi dev-backend dev-frontend test test-backend test-frontend lint fmt build clean

install: install-backend install-frontend

install-backend:
	python3 -m venv $(BACKEND)/.venv
	$(PY)/pip install --upgrade pip
	cd $(BACKEND) && .venv/bin/pip install -e ".[dev]"

install-frontend:
	cd $(FRONTEND) && npm ci --no-audit --no-fund

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

prod:
	docker compose -f docker-compose.prod.yml --env-file .env up -d --build

migrate:
	cd $(BACKEND) && .venv/bin/alembic upgrade head

seed:
	cd $(BACKEND) && .venv/bin/python -m scripts.seed

openapi:
	cd $(BACKEND) && .venv/bin/python scripts/export_openapi.py ../openapi.json

dev-backend:
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd $(FRONTEND) && npm run dev

test: test-backend test-frontend

test-backend:
	cd $(BACKEND) && .venv/bin/pytest

test-frontend:
	cd $(FRONTEND) && npm test

lint:
	cd $(BACKEND) && .venv/bin/ruff check app tests scripts alembic && .venv/bin/ruff format --check app tests scripts alembic
	cd $(FRONTEND) && npm run lint && npm run typecheck

fmt:
	cd $(BACKEND) && .venv/bin/ruff format app tests scripts alembic && .venv/bin/ruff check --fix app tests scripts alembic

build:
	cd $(FRONTEND) && npm run build

clean:
	rm -rf $(FRONTEND)/.next $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache
	find $(BACKEND) -name "__pycache__" -type d -prune -exec rm -rf {} +
