.PHONY: help install dev run test lint security qa clean

help:
	@echo "benj.office-hero — developer targets"
	@echo ""
	@echo "  make install    Install runtime dependencies"
	@echo "  make dev        Install dev dependencies + activate hooks"
	@echo "  make run        Start FastAPI dev server (requires .env)"
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
	python -c "import stat, pathlib; [f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) for f in pathlib.Path('.githooks').iterdir() if f.is_file() and not f.name.startswith('.')]"
	python -c "import stat, pathlib; [f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) for f in pathlib.Path('scripts').iterdir() if f.suffix == '.sh']"

run:
	bash scripts/start-backend.sh

test:
	python -m pytest -q --tb=short

lint:
	python -m pre_commit run --all-files

security:
	@echo "--- bandit ---"
	python -m bandit -r src -ll
	@echo "--- pip-audit ---"
	python -m pip_audit --desc

qa: lint security test
	@echo "All quality gates passed."

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name coverage.xml -delete 2>/dev/null || true
	find . -name .coverage -delete 2>/dev/null || true

# database convenience targets

# Apply all pending Alembic migrations using the DATABASE_URL environment variable
# (the URL must point to the desired database or branch). This target is a no-op
# when the schema is already up-to-date.
db-migrate:
	alembic upgrade head

# Open a psql shell connected to DATABASE_URL.  Requires the `psql` client to
# be installed and on PATH.  Use ``make db-shell`` after exporting
# DATABASE_URL to explore the test/production database.
db-shell:
	@python -c "import os, subprocess, sys; url=os.environ.get('DATABASE_URL');
	if not url: sys.exit('DATABASE_URL not set');
	subprocess.run(['psql', url])"
