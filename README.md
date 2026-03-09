# benj.office-hero

Office Hero web application with automated backend management via git hooks.

## Quick Start

Clone and setup in two steps:

```bash
# 1. Clone the repository
git clone <url> office-hero-mobile
cd office-hero-mobile

# 2. Run setup (choose your platform)
bash scripts/setup-dev.sh        # Linux / macOS / Git Bash
.\scripts\setup-dev.ps1          # Windows PowerShell
```

✅ That's it! The setup script will:

- Configure git hooks for automatic backend management
- Install all Node.js dependencies
- Create development environment files
- Verify your setup with pre-commit

**For detailed rehydration instructions**, see [SETUP.md](SETUP.md) (highly recommended).

## Git Hooks (Automatic)

Once setup runs, git hooks automatically manage your development environment:

| Hook | Purpose | Trigger |
|------|---------|---------|
| **pre-commit** | Linting, formatting, security | Before `git commit` |
| **post-merge** | Backend health check + auto-start | After `git pull` / `git merge` |
| **post-checkout** | Environment verification | After `git checkout` |

Example: Backend automatically restarts if it crashes during a pull

```bash
$ git pull
✅ Backend is running on port 8000
```

## Quality Gates

| Gate | Tool | When | Skip? |
|------|------|------|-------|
| TypeScript | tsc | commit | `git commit --no-verify` |
| ESLint | eslint | commit | `git commit --no-verify` |
| Prettier | prettier | commit | `git commit --no-verify` |
| Pre-commit | pre-commit | commit | `git commit --no-verify` |
| Bandit | bandit | push | — |

Run manually:

```bash
.\scripts\qa_gate.ps1            # Windows
pre-commit run --all-files       # any platform
```

## CI/CD

| Gate | Tool | When |
|------|------|------|
| Markdown lint | markdownlint | commit |
| Python format | black | commit |
| Python lint | ruff | commit |
| File hygiene | pre-commit-hooks | commit |
| Security scan | bandit | push |
| Unit tests (includes ADR compliance checks) | pytest | CI |
| Coverage | pytest-cov | CI |

- **Linting** — TypeScript, ESLint, Prettier, markdownlint
- **Security** — Bandit static analysis
- **Testing** — Jest unit tests
- **Coverage** — Coverage reports

## Documentation

- [SETUP.md](SETUP.md) — Detailed setup & rehydration guide (⭐ **read this first!**)
- [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md) — Backend API details
- [REAL_DEVICE_TESTING_2026-03-09.md](REAL_DEVICE_TESTING_2026-03-09.md) — Real device testing results
