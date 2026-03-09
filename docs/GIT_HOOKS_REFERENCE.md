# 📋 Git Hooks Reference Guide

Quick reference for understanding and troubleshooting git hooks in Office Hero development.

---

## Quick Reference

| Hook | Trigger | Action | Fail Behavior |
|------|---------|--------|---------------|
| **pre-commit** | `git commit` | Lint, format, security | ❌ Blocks commit |
| **post-merge** | `git pull`, `git merge` | Check backend health | ⚠️ Warns, continues |
| **post-checkout** | `git checkout` | Verify env state | ℹ️ Informs, continues |

---

## 🔧 pre-commit Hook

### What it does (pre-commit)

Prevents commits with code quality issues. Runs automatically before each commit.

### Checks performed (pre-commit)

```text
✓ TypeScript compilation (tsc --noEmit)
✓ ESLint (11 rules – syntax, imports, best practices)
✓ Prettier formatting (code style consistency)
✓ Bandit (Python/security analysis, if applicable)
✓ YAML validation
✓ TOML validation
✓ File hygiene (no large files, trailing whitespace)
```

### What happens when it fails

```bash
$ git commit -m "Add new feature"
Pre-commit checking...
❌ ESLint: Unused variable on line 42
❌ Prettier: Invalid formatting on lines 15-20

Commit blocked. Fix issues or:
git commit --no-verify    # (not recommended)
```

### When to skip it

Only when absolutely necessary:

```bash
git commit --no-verify          # Skip all pre-commit checks
pre-commit run --all-files      # Manually run checks
```

### Troubleshooting

```bash
# Run checks manually to debug
pre-commit run --all-files

# Apply automatic fixes
npx eslint . --fix              # Fix ESLint issues
npx prettier --write .          # Fix formatting

# Then commit again
git commit -m "..."
```

---

## 🔄 post-merge Hook

### What it does (post-merge)

Ensures the backend API server is running after pulling changes. Runs automatically after `git pull`, `git merge`, or `git rebase`.

### How it works

**Step 1: Check if backend running**

```bash
curl http://localhost:8000/health
```

**Step 2: If running** ✅

```bash
✅ Backend is running on port 8000
# Continues immediately
```

**Step 3: If NOT running** 🚀

```bash
ℹ️  Backend not running. Starting...

# 1. Searches for backend directory:
#    - ../../office-hero-backend-core (monorepo root)
#    - ../office-hero-backend-core (sibling)
#    - office-hero-backend-core (same dir)

# 2. Executes start script:
#    - ./start_backend.ps1 (Windows)
#    - bash start_backend.sh (Unix)

# 3. Waits up to 10 seconds for startup

# 4. Verifies with health check

✅ Backend is running on port 8000
```

### Example output after pull

```bash
$ git pull
Updating abc123..def456
Fast-forward
 src/screens/home.tsx | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)

post-merge: Checking backend...
✅ Backend is running on port 8000
```

### When it helps

- After long work sessions (backend may have crashed)
- After switching branches (backend state may be stale)
- After merging changes (database schema may have changed)
- When team member has committed backend changes

### When it doesn't help

If backend can't find required environment variables:

```bash
# Check that backend has:
# - DATABASE_URL environment variable
# - JWT_PRIVATE_KEY environment variable
# - JWT_PUBLIC_KEY environment variable

# Set manually if needed:
export DATABASE_URL="postgresql+asyncpg://postgres:pass@localhost:5432/test"
export JWT_PRIVATE_KEY="private"
export JWT_PUBLIC_KEY="public"

# Then manually start backend
bash start_backend.sh  # or .\start_backend.ps1
```

### Troubleshooting (post-merge)

**Problem: "Backend directory not found"**

```bash
# Solution: Backend must be in one of these locations:
ls ../../office-hero-backend-core      # MonoRepo root
ls ../office-hero-backend-core         # Sibling directory
ls office-hero-backend-core            # Same directory

# If not present, clone it:
cd ..
git clone <backend-url> office-hero-backend-core
cd office-hero-mobile
git pull              # Triggers post-merge again
```

**Problem: "Backend failed to start"**

```bash
# Solution: Check for environment variables
echo $DATABASE_URL
echo $JWT_PRIVATE_KEY
echo $JWT_PUBLIC_KEY

# Check for port conflicts
lsof -i :8000                         # Unix
Get-NetTCPConnection -LocalPort 8000  # Windows

# Kill existing process if needed
kill -9 $(lsof -t -i :8000)                    # Unix
Stop-Process -Name python -ErrorAction SilentlyContinue  # Windows

# Try manual startup for debugging
cd office-hero-backend-core
bash start_backend.sh                 # Shows full error output
```

**Problem: "Port 8000 already in use"**

```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9         # Unix
Get-NetTCPConnection -LocalPort 8000 | Stop-Process  # Windows

# Retry
git pull                              # Triggers post-merge
```

---

## 🌿 post-checkout Hook

### What it does (post-checkout)

Verifies environment is ready after switching branches. Runs automatically after `git checkout <branch>`.

### Checks performed (post-checkout)

```text
✓ .env.local file exists (development config)
✓ node_modules directory exists (if package.json present)
✓ Dependencies up-to-date (suggests pnpm install if needed)
```

### What happens when it runs

```bash
$ git checkout feature/new-screen
Switched to branch 'feature/new-screen'

post-checkout: Verifying project state...
✅ Environment file present
```

### When it warns

```bash
$ git checkout feature/with-new-deps
Switched to branch 'feature/with-new-deps'

post-checkout: Verifying project state...
✅ Environment file present
⚠️  Run 'pnpm install' to restore dependencies

# Action: Run suggested command
pnpm install
```

### It never blocks

Unlike pre-commit, post-checkout failures don't prevent branch switching. It only provides informational warnings.

---

## Manual Hook Execution

### Run hooks manually

```bash
# Run a specific hook
./.githooks/pre-commit
./.githooks/post-merge
./.githooks/post-checkout

# Or trigger via git commands
git merge branch-name           # Triggers post-merge
git checkout branch-name        # Triggers post-checkout
git commit -m "message"         # Triggers pre-commit
```

### Skip a hook

```bash
git commit --no-verify          # Skip pre-commit
git merge --no-verify           # Skip post-merge (not standard)
```

### Temporarily disable all hooks

```bash
git config core.hooksPath /dev/null     # Disable all hooks
git config core.hooksPath .githooks     # Re-enable all hooks
```

### Disable specific hook

```bash
mv .githooks/post-merge .githooks/post-merge.disabled
# Do work...
mv .githooks/post-merge.disabled .githooks/post-merge
```

---

## Debugging Hooks

### Enable verbose output

```bash
# For bash hooks, run with -x flag
bash -x ./.githooks/post-checkout

# For PowerShell hooks
powershell -File .\.githooks\post-merge -Verbose
```

### Check if hooks are being called

```bash
# Most hooks print output to console:
git pull              # You'll see hook output
git commit -m "test"  # You'll see check results
git checkout branch   # You'll see verification

# Check git configuration
git config core.hooksPath
# Should output: .githooks
```

### Test hook functionality

```bash
# Test backend health check
curl http://localhost:8000/health

# Test backend startup
bash office-hero-backend-core/start_backend.sh

# Test pre-commit checks
pre-commit run --all-files
```

---

## Common Issues & Solutions

### Hooks "disappeared" after fresh install

**Problem:** Running `npm install` or `pnpm install` wipes `.git/hooks`

**Solution:** Re-run once after installing dependencies

```bash
git config core.hooksPath .githooks
```

### Hooks work in terminal but not in IDE

**Problem:** IDE Git client may not be git CLI and may have its own hook system

**Solution:**

- Use terminal for commits in monorepo
- Or: Install IDE extension for git hooks support
- Or: Disable IDE's builtin git detection

### "Permission denied" when hooks run

**Problem:** Hook files not executable

**Solution:**

```bash
chmod +x .githooks/*
git config core.hooksPath .githooks   # Also reconfigure
```

### Slow commits (pre-commit takes 10+ seconds)

**Problem:** Running too many checks or checking large files

**Solution:**

```bash
# Check which checks are slow
pre-commit run --all-files --verbose

# Some checks can be optimized in config
# Or: Use --no-verify for emergency commits (not recommended)
```

---

## Documentation Index

| Document | Purpose |
|----------|---------|
| [SETUP.md](../SETUP.md) | **Start here**: Setup instructions for new developers |
| [REHYDRATION.md](../REHYDRATION.md) | Deep dive into rehydration system architecture |
| [GIT_HOOKS_REFERENCE.md](GIT_HOOKS_REFERENCE.md) | This document: Hook troubleshooting and reference |
| [README.md](../README.md) | Project overview |

---

**Last Updated:** 2026-03-09
**Hook Status:** ✅ All hooks active and rehydration-ready
