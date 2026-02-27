.PHONY: help setup install install-dev lint format test test-cov test-integration clean run run-dev auth-google list-sources

.DEFAULT_GOAL := help

PYTHON := python3
PIP := pip3

help:
	@echo "Public Finance Data Hub - Development Tasks"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup              Install dependencies and pre-commit hooks"
	@echo "  make install            Install package in development mode"
	@echo "  make install-dev        Install with dev dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint               Run linting checks (flake8)"
	@echo "  make format             Format code (black + isort)"
	@echo "  make format-check       Check if code needs formatting"
	@echo "  make type-check         Run type checking (mypy)"
	@echo ""
	@echo "Testing:"
	@echo "  make test               Run all tests"
	@echo "  make test-cov           Run tests with coverage report"
	@echo "  make test-integration   Run integration tests only"
	@echo "  make test-watch         Run tests on file changes (requires pytest-watch)"
	@echo ""
	@echo "CLI Commands:"
	@echo "  make list-sources       List available data sources"
	@echo "  make auth-google        Setup Google OAuth authentication"
	@echo "  make run-ingest-bcb     Example: Ingest BCB macroeconomic data"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              Remove cache, builds, test artifacts"
	@echo "  make clean-data         Remove downloaded data (CAREFUL!)"
	@echo "  make clean-all          Remove everything including venv"

setup: install install-dev
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "\n✓ Setup complete! To activate the environment:"
	@echo "  source venv/bin/activate  (macOS/Linux)"
	@echo "  venv\\Scripts\\activate   (Windows)"

install:
	@echo "Installing package in development mode..."
	$(PIP) install -e .

install-dev: install
	@echo "Installing dev dependencies..."
	$(PIP) install -e ".[dev]"

format:
	@echo "Formatting code with black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/
	@echo "✓ Code formatted"

format-check:
	@echo "Checking code format (black)..."
	black --check src/ tests/
	@echo "Checking import order (isort)..."
	isort --check-only src/ tests/

lint: format-check
	@echo "Running flake8..."
	flake8 src/ tests/ --max-line-length=100 --exclude=venv,build
	@echo "✓ Linting passed"

type-check:
	@echo "Running mypy type checking..."
	mypy src/
	@echo "✓ Type checking passed"

test:
	@echo "Running pytest..."
	pytest tests/ -v --tb=short

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src/public_finance_data_hub --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report generated in htmlcov/index.html"

test-integration:
	@echo "Running integration tests only..."
	pytest tests/ -v -m integration

list-sources:
	@echo "Available data sources:"
	pfdh list-sources

auth-google:
	@echo "Starting Google OAuth setup..."
	pfdh auth-google

run-ingest-bcb:
	@echo "Ingesting BCB macroeconomic data (example)..."
	pfdh ingest --source bcb --from 2020-01-01 --to 2026-12-31 --log-level INFO

run-dev:
	@echo "Running CLI in development mode..."
	PYTHONPATH=src $(PYTHON) -m public_finance_data_hub.cli --help

clean:
	@echo "Cleaning cache, builds, and test artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	rm -rf build/ dist/ .eggs/
	@echo "✓ Clean complete"

clean-data:
	@echo "WARNING: Removing downloaded data..."
	@read -p "Are you sure? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		rm -rf data/raw data/curated data/manifests; \
		echo "✓ Data removed"; \
	fi

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf venv/ .venv/
	@echo "✓ Full cleanup complete"

.PHONY: venv
venv:
	$(PYTHON) -m venv venv
	@echo "✓ Virtual environment created"
	@echo "Activate with: source venv/bin/activate"
