COMPOSE = docker compose -f docker/docker-compose.yml

.PHONY: up down logs dev dev-api dev-web install lint typecheck test

## Infra
up:        ## Start Postgres, Redis, ChromaDB
	$(COMPOSE) up -d
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f

## Install deps
install:
	pip install -e apps/api -e packages/router -e packages/memory -r requirements-dev.txt
	pnpm install

## Dev servers (run in separate terminals)
dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000
dev-web:
	pnpm --filter web dev
dev:
	@echo "Run 'make dev-api' and 'make dev-web' in separate terminals."
	@echo "API -> http://localhost:8000/health   Web -> http://localhost:3000"

## Checks
lint:
	ruff check .
	pnpm --filter web lint
typecheck:
	mypy
	pnpm --filter web exec tsc --noEmit
test:
	pytest
