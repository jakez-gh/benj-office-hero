# Git Hooks & Quality Gates Rehydration Guide

This document describes how to fully rehydrate all git hooks, pre-commit checks, and CI/CD pipelines from the GitHub repository.

## Quick Start

After cloning the repository, run the appropriate setup script for your OS:

```bash
# Linux / macOS / Git Bash on Windows
bash scripts/setup-dev.sh

# Windows PowerShell
.\scripts\setup-dev.ps1
```

This single command will:

1. ✅ Configure git to use `.githooks/` for all hooks
2. ✅ Initialize git submodules (ai-project-guide documentation)
3. ✅ Install all Python development dependencies
4. ✅ Verify hook installation and display next steps

---

## What Gets Rehydrated

### 1. Local Git Hooks (.githooks/)

| Hook | Purpose | When Triggered |
|---|---|---|
| **pre-commit** | Lint, format, file hygiene | Before each commit |
| **commit-msg** | Reserved — no hooks configured yet | After commit message is written |
| **pre-push** | Tests + bandit + pip-audit | Before pushing to remote |

> **Note:** The `commit-msg` shim is wired up but no hooks are configured for
> that stage in `.pre-commit-config.yaml`. It is reserved for future commit
> message validation (e.g. commitlint, Conventional Commits).

**Location:** `.githooks/` directory

**How they're installed:**

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

### 2. Pre-Commit Framework Configuration

**File:** `.pre-commit-config.yaml`

**Includes:** 15 hooks across 7 categories

| Category | Tools | When |
|---|---|---|
| Markdown | markdownlint (auto-fix) | pre-commit |
| Python formatting | black | pre-commit |
| Python linting | ruff (auto-fix) | pre-commit |
| File hygiene | trailing-whitespace, end-of-file-fixer, check-yaml, check-toml, check-json, check-added-large-files, check-merge-conflict, mixed-line-ending, detect-private-key | pre-commit |
| CVE scanning | pip-audit | pre-push |
| Security | bandit static analysis | pre-push |
| Testing | pytest (TDD gate) | pre-push |

### 3. Python Dependencies

**File:** `pyproject.toml` → `[project.optional-dependencies]dev`

```toml
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",  # ← async test fixtures
    "pytest-cov>=4.1",
    "pre-commit>=4.0",        # ← Pre-commit framework
    "ruff>=0.8",              # ← Python linting
    "black>=24.0",            # ← Python formatting
    "bandit>=1.8",            # ← Security scanning
    "hypothesis>=6.88",
    "pytest-xdist>=3.5",
    "pytest-timeout>=2.2",
    "aiosqlite>=0.18",
]
```

### 4. GitHub Actions CI/CD

**Files:** `.github/workflows/ci.yml`, `.github/workflows/security.yml`

**Runs on:**

- Every push to any branch
- Every pull request
- Scheduled security scans (4x daily)

**Pipeline:**

1. **Lint** (ubuntu-latest)
   - Pre-commit hooks (black, ruff, markdownlint, file checks)
   - Creates GitHub issues on failure

2. **Security** (ubuntu-latest)
   - Bandit static analysis (-ll = low+medium severity)
   - pip-audit dependency CVE scan

3. **Test** (ubuntu-latest)
   - pytest with coverage reporting
   - Creates GitHub issues on test failure

### 5. Git Submodules

**File:** `.gitmodules`

```properties
[submodule "project-documents/ai-project-guide"]
    path = project-documents/ai-project-guide
    url = https://github.com/ecorkran/ai-project-guide.git
```

**Initialized by:** `setup-dev.sh` / `setup-dev.ps1` with `git submodule update --init --recursive`

---

## Rehydration Flow

### Initial Setup (First Clone)

```text
Clone → setup-dev.sh / .ps1 → configure hooksPath → init submodules → install deps → verify
```

### Per-Commit Workflow

1. Edit files
2. `git add` — stage changes
3. `git commit` — pre-commit hook runs lint/format/hygiene; auto-fixes are applied inline
4. `git push` — pre-push hook runs `pytest`, `bandit`, `pip-audit` (slow; ~30–90 s)

### Skip Hooks (Emergency Only)

```bash
# Skip all pre-commit checks
git commit --no-verify

# Skip all pre-push checks
git push --no-verify

# Skip specific hooks (use SKIP env var)
SKIP=bandit,pytest-check git push
```

---

## Troubleshooting

### Problem: Hooks not running

**Solution 1: Reconfigure git hooks path**

```bash
git config core.hooksPath .githooks
```

**Solution 2: Reinstall from scratch**

```bash
# Windows
.\scripts\setup-dev.ps1

# Linux/macOS/Git Bash
bash scripts/setup-dev.sh
```

---

### Problem: Pre-commit not found

**Error:** `pre-commit: command not found`

**Solution:** Install development dependencies

```bash
pip install -e ".[dev]"
```

---

### Problem: Tests fail on push

**What happens:** pre-push hook runs `pytest` and blocks the push

**Options:**

1. **Fix the test** — Recommended, ensures code quality
2. **Skip hook** — Emergency only

   ```bash
   SKIP=pytest-check git push
   ```

---

### Problem: Bandit security scan fails

**What happens:** pre-push hook runs `bandit -r src -ll` and blocks the push

**Options:**

1. **Fix the security issue** — Recommended
2. **Skip hook** — Emergency only

   ```bash
   SKIP=bandit git push
   ```

---

## Manual Quality Gate Checks

Run these commands anytime to check code quality without committing:

```bash
# All pre-commit checks (without committing)
pre-commit run --all-files

# Lint only
ruff check src/

# Format check
black --check src/

# Security scan
bandit -r src -ll

# Tests
pytest -q --tb=short

# Coverage report
pytest --cov=src --cov-report=html

# Full quality gate (lint + security + test)
make qa
```

---

## CI/CD Pipeline Details

### GitHub Actions: ci.yml

**Triggers:** `push` to any branch, `pull_request` to any branch

**Jobs:**

1. **lint** (~ 2 min) — `pre-commit run --all-files`
2. **security** (~ 3 min) — bandit + pip-audit
3. **test** (~ 5 min) — pytest with coverage

### GitHub Actions: security.yml

**Schedule:** 4x daily (06:00, 12:00, 18:00, 00:00 UTC)

**Jobs:**

- Dependency vulnerability audit (pip-audit)
- Bandit static analysis with JSON report artifact

---

## Files Summary

| File | Purpose |
|---|---|
| `.githooks/pre-commit` | Pre-commit hook shim |
| `.githooks/commit-msg` | Commit-msg shim (reserved, no active hooks) |
| `.githooks/pre-push` | Pre-push hook shim |
| `.pre-commit-config.yaml` | Quality gate definitions (15 hooks) |
| `.github/workflows/ci.yml` | CI pipeline |
| `.github/workflows/security.yml` | Scheduled security pipeline |
| `pyproject.toml` | Dev dependency definitions |
| `scripts/setup-dev.sh` | Unix/Linux/macOS one-command setup |
| `scripts/setup-dev.ps1` | Windows PowerShell one-command setup |
| `.gitmodules` | Submodule references |

---

## Verification Checklist

After running setup, verify everything is working:

```bash
# Check 1: Hooks are configured
git config core.hooksPath              # Should output: .githooks

# Check 2: Dependencies are installed
pip list | grep -E "pre-commit|bandit|ruff"

# Check 3: Pre-commit can run
pre-commit run --all-files             # Should pass all checks

# Check 4: Submodules are initialized  (bash / Git Bash only)
ls -la project-documents/ai-project-guide/

# Check 5: Tests can run
pytest --co -q                         # Should collect tests without error
```

---

## Additional Resources

- **Pre-commit Framework:** <https://pre-commit.com/>
- **Ruff Documentation:** <https://docs.astral.sh/ruff/>
- **Black Documentation:** <https://black.readthedocs.io/>
- **Bandit Documentation:** <https://bandit.readthedocs.io/>
- **pytest Documentation:** <https://docs.pytest.org/>
