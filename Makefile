.PHONY: help install dev frontend migrate migrate-new migrate-down \
        test test-cov test-fast lint format clean docker-up docker-down docker-logs db-shell

# ── Paths — always use the project venv, not global installs ─────────────────
VENV      = .venv
PYTHON    = $(VENV)/bin/python
PIP       = $(VENV)/bin/pip
ALEMBIC   = $(VENV)/bin/alembic
PYTEST    = $(VENV)/bin/pytest
UVICORN   = $(VENV)/bin/uvicorn
STREAMLIT = $(VENV)/bin/streamlit
RUFF      = $(VENV)/bin/ruff

help:  ## Show available make targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────────────────────────
install:  ## Create venv and install all dependencies
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	@echo "\n✅ Done. Activate with: source $(VENV)/bin/activate"

# ── Development ───────────────────────────────────────────────────────────────
dev:  ## Start PostgreSQL + run migrations + start FastAPI (hot reload)
	@echo "Starting PostgreSQL..."
	docker compose up postgres -d
	@echo "Waiting for PostgreSQL health check..."
	@until docker exec shopmind_postgres pg_isready -U shopmind -d shopmind_db -q; do sleep 1; done
	@echo "Running migrations..."
	$(ALEMBIC) upgrade head
	@echo "Starting API at http://localhost:8000/docs"
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

frontend:  ## Start the Streamlit frontend at http://localhost:8501
	$(STREAMLIT) run frontend/app.py --server.port 8501

# ── Migrations ────────────────────────────────────────────────────────────────
migrate:  ## Apply all pending migrations
	$(ALEMBIC) upgrade head

migrate-new:  ## Create a new migration (usage: make migrate-new MSG="add foo column")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-down:  ## Rollback one migration
	$(ALEMBIC) downgrade -1

# ── Testing ────────────────────────────────────────────────────────────────────
test:  ## Run full test suite
	$(PYTEST) tests/ -v --tb=short

test-cov:  ## Run tests with HTML coverage report
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "\nCoverage report: open htmlcov/index.html"

test-fast:  ## Run only unit tests (no DB, instant)
	$(PYTEST) tests/test_agents/ tests/test_config.py -v --tb=short

# ── Code Quality ──────────────────────────────────────────────────────────────
lint:  ## Lint with ruff
	$(RUFF) check app/ tests/

format:  ## Format with ruff
	$(RUFF) format app/ tests/

lint-fix:  ## Auto-fix lint issues
	$(RUFF) check --fix app/ tests/

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-up:  ## Build and start all services (postgres + api + frontend)
	docker compose up --build -d

docker-down:  ## Stop and remove all containers
	docker compose down

docker-logs:  ## Stream logs from all containers
	docker compose logs -f

# ── Utilities ──────────────────────────────────────────────────────────────────
clean:  ## Remove build artifacts and caches
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	rm -rf .coverage htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/

db-shell:  ## Open a psql shell in the running postgres container
	docker exec -it shopmind_postgres psql -U shopmind -d shopmind_db
