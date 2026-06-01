.PHONY: help install dev migrate test lint format clean docker-up docker-down

# ── Variables ─────────────────────────────────────────────────────────────────
PYTHON = python
PIP = pip
ALEMBIC = alembic
PYTEST = pytest
UVICORN = uvicorn
STREAMLIT = streamlit

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ──────────────────────────────────────────────────────────────────────
install:  ## Install all dependencies in a virtualenv
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt
	@echo "\n✅ Dependencies installed. Activate with: source .venv/bin/activate"

# ── Development ───────────────────────────────────────────────────────────────
dev:  ## Start PostgreSQL + FastAPI backend (with hot reload)
	@echo "Starting PostgreSQL..."
	docker compose up postgres -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 3
	@echo "Running migrations..."
	$(ALEMBIC) upgrade head
	@echo "Starting FastAPI..."
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

frontend:  ## Start the Streamlit frontend
	$(STREAMLIT) run frontend/app.py --server.port 8501

migrate:  ## Run database migrations
	$(ALEMBIC) upgrade head

migrate-new:  ## Create a new migration (usage: make migrate-new MSG="add column")
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

migrate-down:  ## Rollback one migration
	$(ALEMBIC) downgrade -1

# ── Testing ────────────────────────────────────────────────────────────────────
test:  ## Run all tests
	$(PYTEST) tests/ -v --tb=short

test-cov:  ## Run tests with coverage report
	$(PYTEST) tests/ -v --cov=app --cov-report=term-missing --cov-report=html

test-fast:  ## Run only unit tests (no DB required)
	$(PYTEST) tests/test_agents/ -v --tb=short

# ── Code quality ───────────────────────────────────────────────────────────────
lint:  ## Run ruff linter
	ruff check app/ tests/

format:  ## Format code with ruff
	ruff format app/ tests/

# ── Docker ─────────────────────────────────────────────────────────────────────
docker-up:  ## Start all services with Docker Compose
	docker compose up --build -d

docker-down:  ## Stop all Docker services
	docker compose down

docker-logs:  ## Tail Docker logs
	docker compose logs -f

# ── Utilities ──────────────────────────────────────────────────────────────────
clean:  ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .coverage htmlcov/ .mypy_cache/ .ruff_cache/ .pytest_cache/

db-shell:  ## Connect to PostgreSQL via psql
	docker exec -it shopmind_postgres psql -U shopmind -d shopmind_db
