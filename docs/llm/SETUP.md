# 🔄 Office Hero Development Setup & Rehydration Guide

## Quick Start (30 seconds)

After cloning the repository, run **one** of these commands based on your platform:

**Windows (PowerShell):**

```powershell
.\scripts\setup-dev.ps1
```

**macOS/Linux/Git Bash:**

```bash
bash scripts/setup-dev.sh
```

That's it! Your development environment is now configured with all necessary dependencies and git hooks.

---

## What is "Rehydration"?

Rehydration means that when you clone the repository, everything needed for development is **automatically restored**:

✅ Git hooks are configured
✅ Node.js dependencies are installed
✅ Environment files are created
✅ Backend auto-startup is enabled

You never have to manually configure hooks or environment variables again.

---

## How It Works

### 1. **Initial Setup** (Run Once After Clone)

Execute the setup script for your platform (see Quick Start above). This:

- Configures git to use hooks from `.githooks/` directory
- Installs Node.js dependencies via pnpm/npm
- Creates `.env.local` with development defaults
- Installs pre-commit framework (if available)

### 2. **Automatic Backend Management** (Continuous)

Once setup is complete, git hooks automatically manage the backend:

| Hook | When | Action |
|------|------|--------|
| **pre-commit** | Before commits | Runs linting, formatting, security checks |
| **post-merge** | After pulling/merging | Checks if backend is running; auto-starts if needed |
| **post-checkout** | After branch switches | Verifies environment state |

#### Example: Backend Auto-Start on Pull

```bash
$ git pull
# ↓ Automatically runs post-merge hook
✅ Backend is running on port 8000
```

If backend crashed:

```bash
$ git pull
# ↓ Automatically runs post-merge hook
⚠️  Backend not running - auto-starting...
✅ Backend started successfully on port 8000
```

---

## Git Hooks Included

### 🔧 **pre-commit**: Code Quality

**Runs:** Before each commit
**Checks:**

- Typescript compilation (`tsc --noEmit`)
- ESLint (11 rules)
- Prettier formatting
- Security checks (bandit)
- YAML/TOML validation

**Skip if needed:** `git commit --no-verify`

### 🔄 **post-merge**: Backend Health

**Runs:** After `git pull`, `git merge`, rebases
**Actions:**

- Checks if backend process is running on port 8000
- If missing, retrieves backend location and auto-starts
- Logs startup activity to `.backend-startup.log`

**Backend must be discoverable in one of these locations:**

```bash
../../office-hero-backend-core
../office-hero-backend-core
office-hero-backend-core
```

### 🌿 **post-checkout**: Environment Verification

**Runs:** After branch switches
**Checks:**

- Node.js version compatibility
- Environment variables (EXPO_PUBLIC_OFFICE_HERO_API_URL)
- Backend availability

---

## Configuration Files

### 📝 `.env.local` (Git-Ignored)

Development environment configuration created by setup script:

```bash
# Backend API endpoint for development
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
```

**Note:** This file is git-ignored and unique to each developer's machine.

### 📝 `.githooks/` Directory

Contains all git hooks. Committed to repository for easy sharing:

- `pre-commit` - Linting/security
- `post-merge` - Backend health
- `post-checkout` - Environment verification

### 📝 `scripts/setup-dev.sh` & `setup-dev.ps1`

Setup orchestration scripts. Run once after cloning to initialize everything.

---

## Backend Integration

The backend is **NOT** started by the setup script—instead, git hooks handle it:

1. **First pull/merge after setup:** post-merge hook detects backend is missing, auto-starts it
2. **Subsequent pulls:** post-merge hook verifies backend is still running, restarts if crashed
3. **Branch switches:** post-checkout hook verifies environment

### Manual Backend Control

If you need to manually control the backend:

**Start backend:**

```bash
cd office-hero-backend-core
./start_backend.sh          # Linux/macOS
.\start_backend.ps1         # Windows
```

**Stop backend:**

```powershell
Stop-Process -Name python -Filter {$_.Port -eq 8000}  # Windows
kill $(lsof -t -i :8000)                              # Linux/macOS
```

**Check status:**

```bash
curl http://localhost:8000/health
# {"status": "healthy"}
```

---

## Troubleshooting

### ❌ Setup script fails to find pnpm/npm

**Solution:** Install Node.js and pnpm

```bash
brew install node pnpm      # macOS
apt install nodejs npm      # Linux
# Windows: Download from nodejs.org
```

### ❌ Backend not auto-starting

**Check 1:** Backend repository location

```bash
# Backend must be in one of these paths:
../../office-hero-backend-core
../office-hero-backend-core
office-hero-backend-core
```

**Check 2:** View hook logs

```bash
tail -f .backend-startup.log
```

**Check 3:** Manually test backend

```bash
cd office-hero-backend-core
bash start_backend.sh    # or .\start_backend.ps1
```

### ❌ Port 8000 already in use

**Solution:** Kill existing process

```powershell
# Windows
Stop-Process -Name python -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Stop-Process

# Linux/macOS
lsof -ti:8000 | xargs kill -9
```

### ❌ Hooks not running

**Verify configuration:**

```bash
git config core.hooksPath
# Should output: .githooks
```

**Re-configure if needed:**

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

### ❌ Environment variables not loaded in .env.local

**Check file exists:**

```bash
ls -la apps/tech-mobile/.env.local
```

**Recreate if missing:**

```bash
cat > apps/tech-mobile/.env.local << EOF
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
EOF
```

---

## Advanced: Customizing Hook Behavior

### Custom Backend Port

Edit `.githooks/post-merge` and change:

```bash
BACKEND_PORT=8000  # ← Change this
```

### Custom Backend Startup Command

Edit `.githooks/post-merge` and modify the `start_backend()` function.

### Disabling Auto-Start

To temporarily disable backend auto-start:

```bash
# Rename the hook temporarily
mv .githooks/post-merge .githooks/post-merge.disabled
```

Re-enable:

```bash
mv .githooks/post-merge.disabled .githooks/post-merge
```

---

## Docker Alternative (Coming Soon)

For fully isolated development, dockerized setup with:

- PostgreSQL database container
- Backend FastAPI container
- Pre-configured volumes for code sharing

This will eliminate environment setup differences across developers.

---

## FAQ

**Q: Do I have to run setup-dev.sh every time I clone?**
A: No, only once after initial clone. Setup commits the configuration to git.

**Q: Can I disable the backend auto-start hook?**
A: Yes, rename `.githooks/post-merge` to `.githooks/post-merge.disabled`

**Q: What if I'm on Windows without PowerShell?**
A: Use Git Bash and run `bash scripts/setup-dev.sh` instead

**Q: Do git hooks run in CI/CD?**
A: No, they're local-only. CI/CD uses separate workflows.

**Q: How do I test changes to hook scripts?**
A: Edit the files in `.githooks/` and test manually:

```bash
./.githooks/post-merge       # Run directly
git merge branch-name        # Run via git
```

---

## Related Documentation

- [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md) - Backend API details
- [README.md](README.md) - Project overview
- `.githooks/` - Source code for all hooks

---

**Last Updated:** 2026-03-09
**Rehydration Readiness:** ✅ Fully Automated
