# 🔄 Rehydration System Architecture

**Status:** ✅ Fully Automated | **Last Updated:** 2026-03-09

This document explains how the Office Hero mobile development environment is automatically restored from the GitHub repository through a rehydration system.

---

## What Gets Rehydrated?

When a developer clones the repository and runs the setup script, the following are **automatically restored**:

### ✅ Restored by Setup Script

| Component | Script | Status |
|-----------|--------|--------|
| Git hooks path configuration | `setup-dev.sh` / `setup-dev.ps1` | Configured via `git config core.hooksPath` |
| Node.js dependencies | pnpm/npm | Installed from `package.json` |
| Environment variables | `.env.local` creation | Generated with development defaults |
| Pre-commit framework | pre-commit | Optional; installed if available |

### ✅ Restored by Git Hooks (Continuous)

| Component | Hook | Trigger |
|-----------|------|---------|
| Backend process | `post-merge` | Auto-restart after pull/merge |
| Environment state | `post-checkout` | Verification after branch switch |
| Code quality| `pre-commit` | Checks before each commit |

### 📦 Committed to Repository

These files enable rehydration:

```text
.githooks/
  ├── pre-commit           # Code quality checks
  ├── post-merge           # Backend health management
  └── post-checkout        # Environment verification

scripts/
  ├── setup-dev.sh         # Linux/macOS setup
  ├── setup-dev.ps1        # Windows PowerShell setup
  └── qa_gate.ps1          # Quality gate runner

SETUP.md                    # Setup instructions (this guide)
README.md                   # Project overview with link to SETUP.md
```

### 🔗 Git-Ignored (Per-Developer)

These are created locally and not committed:

```text
.env.local                  # Development backend URL
.backend-startup.log        # Hook execution logs
node_modules/               # NPM dependencies
.git/hooks/                 # Git hooks mirror (created by git config)
office-hero-backend-core/   # Symlinked or cloned separately
```

---

## Execution Flow

### 1️⃣ **Developer Clones Repository**

```bash
git clone <url> office-hero-mobile
cd office-hero-mobile
```

**State:** Repository downloaded, git hooks NOT yet configured

### 2️⃣ **Developer Runs Setup Script**

**Option A: PowerShell (Windows)**

```powershell
> .\scripts\setup-dev.ps1
```

**Option B: Bash (macOS/Linux/Git Bash)**

```bash
bash scripts/setup-dev.sh
```

**State During Setup:**

1. ✅ Git hooks path configured: `git config core.hooksPath .githooks`
2. ✅ Hook files made executable: `chmod +x .githooks/*`
3. ✅ Node.js dependencies installed: `pnpm install`
4. ✅ `.env.local` created with defaults
5. ✅ Pre-commit framework set up (optional)

**State After Setup:**

- Git is now watching `.githooks/` directory
- Any `git merge`, `git pull`, or `git rebase` will trigger `post-merge` hook
- Any `git checkout` will trigger `post-checkout` hook
- Any `git commit` will trigger `pre-commit` hook
- Developer can start working immediately

### 3️⃣ **Developer Pulls Changes** (Continuous)

```bash
git pull
```

**Automatic:** `post-merge` hook executes

```bash
✅ Backend is running on port 8000
# OR
ℹ️  Backend not running. Starting...
✅ Backend is running on port 8000
```

**State:** Developer always has running backend after pulls

### 4️⃣ **Developer Switches Branches**

```bash
git checkout feature/new-screen
```

**Automatic:** `post-checkout` hook executes

```bash
🔧 Post-checkout: Verifying project state...
✅ Environment file present
```

**State:** Environment verified, developer notified if action needed

### 5️⃣ **Developer Commits Code**

```bash
git commit -m "Add new feature"
```

**Automatic:** `pre-commit` hook executes

```bash
Running pre-commit checks...
✅ TypeScript compilation passed
✅ ESLint passed (11 rules)
✅ Prettier formatting OK
✅ Security checks passed
```

**State:** Only high-quality code committed to repository

---

## Hook Architecture

### 🔧 **pre-commit** Hook

**Purpose:** Prevent low-quality code from being committed

**Execution:** Before each `git commit`

**Checks:**

- TypeScript compilation (`tsc --noEmit`)
- ESLint (11 rules)
- Prettier formatting
- Bandit security scan
- YAML/TOML validation

**Failure Behavior:** Commit blocked; developer must fix issues

**Override:** `git commit --no-verify` (not recommended)

**File Location:** [`.githooks/pre-commit`](.githooks/pre-commit)

---

### 🔄 **post-merge** Hook

**Purpose:** Ensure backend server is running after repository changes

**Execution:** After `git merge`, `git rebase`, `git pull`

**Logic:**

```text
IF backend running on port 8000:
    ✅ Print "Backend is running"
ELSE:
    ℹ️  Locate backend directory
    🚀 Start backend process
    ⏳ Wait up to 10 seconds for startup
    IF backend started:
        ✅ Print "Backend is running"
    ELSE:
        ❌ Print error (developer must investigate)
```

**Backend Location Search Order:**

1. `../../office-hero-backend-core` (monorepo root)
2. `../office-hero-backend-core` (sibling directory)
3. `office-hero-backend-core` (same directory as mobile app)

**Startup Command:**

- Windows: `.\start_backend.ps1`
- Unix: `bash start_backend.sh`

**Health Check:** `curl http://localhost:8000/health`

**File Location:** [`.githooks/post-merge`](.githooks/post-merge)

---

### 🌿 **post-checkout** Hook

**Purpose:** Verify environment is ready after branch changes

**Execution:** After `git checkout <branch>`

**Checks:**

- `.env.local` exists
- `node_modules` present (if `package.json` exists)
- Suggests `pnpm install` if dependencies missing

**Failure Behavior:** Non-blocking; provides informational warnings only

**File Location:** [`.githooks/post-checkout`](.githooks/post-checkout)

---

## Setup Scripts in Detail

### 📝 `scripts/setup-dev.ps1` (Windows)

**Language:** PowerShell 5.1+

**Steps:**

1. Configure git hooks path
2. Make hooks executable
3. Install Node.js dependencies (pnpm > npm)
4. Create `.env.local` with defaults
5. Install pre-commit framework (if available)

**Usage:**

```powershell
.\scripts\setup-dev.ps1          # Default: setup all
.\scripts\setup-dev.ps1 -SkipBackendSetup  # Skip backend checks
```

**Color Output:** Yes (cyan, green, yellow, red)

**Error Handling:** Stops on first failure with descriptive message

---

### 📝 `scripts/setup-dev.sh` (Unix)

**Language:** Bash 4+

**Steps:** Same as PowerShell version

**Usage:**

```bash
bash scripts/setup-dev.sh        # Default: setup all
bash scripts/setup-dev.sh -s     # Skip backend setup
```

**Color Output:** Yes (ANSI color codes)

**Error Handling:** Stops on first failure (`set -e`)

**Windows Git Bash:** Fully compatible

---

## Environment Variables

### Development Configuration (`.env.local`)

Auto-created by setup script with sensible defaults:

```bash
# Backend API endpoint for development
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
```

**Git-Ignored:** Yes (`.env.local` in `.gitignore`)

**Per-Developer:** Yes (each developer has unique configuration)

**Required for:** Mobile app API requests to backend

**Modification:** Edit directly or recreate with setup script

---

## Troubleshooting Rehydration

### Scenario 1: "Backend not starting"

**Diagnosis:**

```bash
# Check if backend directory exists
ls -la ../office-hero-backend-core
ls -la ../../office-hero-backend-core

# Check if startup script exists
ls -la ../office-hero-backend-core/start_backend.ps1
```

**Fix:** Ensure backend repository is cloned in expected location:

```bash
# Clone backend next to mobile repo
cd ..
git clone <backend-url> office-hero-backend-core
cd office-hero-mobile
git pull              # Will trigger post-merge and start backend
```

---

### Scenario 2: "Port 8000 already in use"

**Diagnosis:**

```bash
# Windows
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue

# Linux/macOS
lsof -i :8000
```

**Fix:**

```bash
# Windows
Stop-Process -Name python -ErrorAction SilentlyContinue

# Linux/macOS
kill -9 $(lsof -t -i :8000)
```

Then trigger post-merge again:

```bash
git pull
```

---

### Scenario 3: "Hooks not running"

**Diagnosis:**

```bash
git config core.hooksPath
# Should output: .githooks
```

**Fix:** Re-run setup script or manually configure:

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

---

### Scenario 4: ".env.local missing"

**Diagnosis:**

```bash
ls -la apps/tech-mobile/.env.local
```

**Fix:** Recreate with setup script:

```bash
bash scripts/setup-dev.sh
# OR manually:
cat > apps/tech-mobile/.env.local << EOF
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
EOF
```

---

### Scenario 5: "Setup script fails"

**Enable debugging:**

**PowerShell:**

```powershell
.\scripts\setup-dev.ps1 -Verbose
```

**Bash:**

```bash
bash -x scripts/setup-dev.sh
```

This prints each command executed for diagnosis.

---

## Verification Checklist

After running setup, verify rehydration is complete:

- [ ] `git config core.hooksPath` outputs `.githooks`
- [ ] `node_modules/` directory exists
- [ ] `apps/tech-mobile/.env.local` exists
- [ ] `git pull` triggers post-merge hook
- [ ] `curl http://localhost:8000/health` responds with 200 OK
- [ ] `git checkout -b test` works without errors
- [ ] `git commit --allow-empty -m "test"` passes pre-commit checks

---

## Architecture Diagram

```text
GitHub Repository
│
├── .githooks/               ← Committed to repo
│   ├── pre-commit          ← Code quality (runs before commit)
│   ├── post-merge          ← Backend management (runs after pull)
│   └── post-checkout       ← Environment verify (runs after checkout)
│
├── scripts/                ← Committed to repo
│   ├── setup-dev.ps1       ← Windows setup orchestrator
│   ├── setup-dev.sh        ← Unix setup orchestrator
│   └── qa_gate.ps1         ← Manual quality gate runner
│
├── SETUP.md                ← This guide (committed to repo)
├── README.md               ← Project overview (committed to repo)
│
└── apps/tech-mobile/       ← Mobile app code
    ├── package.json        ← Node.js dependencies
    ├── .env.local          ← Git-ignored; created by setup
    └── [source code]
```

---

## One-Command Rehydration

New developers should only need:

```bash
# Step 1: Clone
git clone <url> office-hero-mobile && cd office-hero-mobile

# Step 2: Setup (runs all rehydration)
bash scripts/setup-dev.sh     # Or .\scripts\setup-dev.ps1 on Windows

# Step 3: Done! Start developing
pnpm --filter tech-mobile start
```

---

## Future Enhancements

### Planned Improvements

1. **Docker Rehydration**
   - Pre-configured PostgreSQL + FastAPI containers
   - Eliminates environment differences
   - Single `docker compose up` startup

2. **GitHub Actions Workflows**
   - Auto-run tests on PR
   - Build mobile app artifacts
   - Backend deployment pipeline

3. **CI/CD Integration**
   - E2E testing with real backend
   - Artifact signing
   - Release automation

4. **Platform-Specific Hooks**
   - Separate logic for Windows vs Unix
   - No need for bash on Windows
   - Native PowerShell integration

---

## Related Documentation

- [SETUP.md](SETUP.md) — User-facing setup guide (read this first!)
- [README.md](README.md) — Project overview
- [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md) — Backend API details
- [`.githooks/`](.githooks/) — Source code for all hooks
- [scripts/setup-dev.ps1](scripts/setup-dev.ps1) — Windows setup script
- [scripts/setup-dev.sh](scripts/setup-dev.sh) — Unix setup script

---

**Rehydration System Status:** ✅ **PRODUCTION READY**

All components committed to repository. Ready for team use.
