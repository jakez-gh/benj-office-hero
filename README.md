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

## Frontend Definition of Done (DoD)

### Milestone DoD (required for every milestone)

A milestone is only done when **all** items below are true:

1. **Feature scope complete**
	- The planned UI behavior for that milestone is implemented and accessible from the app navigation.
2. **Quality gates pass**
	- Relevant checks are green (TypeScript, ESLint, Prettier, and any affected tests).
3. **No regressions observed**
	- Existing core flows still work (login, shell navigation, and previously completed pages).
4. **Verified screenshot evidence exists (mandatory)**
	- At least one screenshot per milestone is captured.
	- Screenshot must clearly show the milestone behavior (not just a page shell).
	- Screenshot must be reviewed and explicitly marked as verified in the PR description/checklist.
5. **PR notes are complete**
	- PR includes what was delivered, what was tested, and the screenshot verification note.

### Recommended frontend milestone checkpoints

- **M1 — Auth + Admin shell visible**
  - Login flow works and nav shell loads.
  - **Verified screenshot:** logged-in shell with all expected nav items visible.
- **M2 — Dispatch page functional**
  - Dispatch page renders real states and handles primary user action(s).
  - **Verified screenshot:** dispatch UI after successful action/state update.
- **M3 — Jobs page functional**
  - Jobs list/details render correctly and actions behave as expected.
  - **Verified screenshot:** jobs UI showing loaded data and an action result.
- **M4 — Users/Vehicles complete + UX polish**
  - Users and vehicles flows are usable and consistent with app patterns.
  - **Verified screenshot:** users and vehicles screens in functional state.

### Branch-level DoD (`stream/frontend`)

The branch is done only when:

- All planned frontend milestones are individually marked done.
- Every milestone has at least one **verified** screenshot artifact.
- End-to-end user path is intact: login → navigate → perform key page actions.
- No known P1/P2 frontend defects remain open.
- Required checks are green and branch is merge-ready.
- PR summary includes a milestone-by-milestone evidence list with screenshot verification status.

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
