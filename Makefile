.PHONY: help install dev test lint security qa clean

help:
	@echo "benj.office-hero — developer targets"
	@echo ""
	@echo "  make install    Install runtime dependencies"
	@echo "  make dev        Install dev dependencies + activate hooks"
	@echo "  make test       Run pytest"
	@echo "  make lint       Run pre-commit on all files"
	@echo "  make security   Run bandit + pip-audit"
	@echo "  make qa         Run all quality gates (lint + security + test)"
	@echo "  make clean      Remove build/cache artifacts"

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	git config core.hooksPath .githooks

test:
	python -m pytest -q --tb=short

lint:
	python -m pre_commit run --all-files

security:
	@echo "--- bandit ---"
	@if find src -name "*.py" 2>/dev/null | grep -q .; then \
		python -m bandit -r src -ll; \
	else \
		echo "No Python files in src/ yet."; \
	fi
	@echo "--- pip-audit ---"
	pip-audit --desc

qa: lint security test
	@echo "All quality gates passed."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name coverage.xml -delete 2>/dev/null || true
	find . -name .coverage -delete 2>/dev/null || true
