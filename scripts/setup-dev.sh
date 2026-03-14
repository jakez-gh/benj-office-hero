#!/usr/bin/env bash
# setup-dev.sh — First-time developer setup (Linux / macOS / Git Bash on Windows)
# Run once after cloning: bash scripts/setup-dev.sh
set -e

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

write_header()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}"; }
write_success() { echo -e "  ${GREEN}✓ $1${NC}"; }
write_warning() { echo -e "  ${YELLOW}⚠️  $1${NC}"; }
write_error()   { echo -e "  ${RED}❌ $1${NC}"; }

write_header "Office Hero Development Setup"

# 1. Configure Git hooks
echo -e "\n${CYAN}1️⃣  Configuring Git hooks...${NC}"
git config core.hooksPath .githooks
write_success "Git hooks path configured (.githooks)"

# 2. Make hooks executable
echo -e "\n${CYAN}2️⃣  Ensuring hook scripts are executable...${NC}"
chmod +x .githooks/* 2>/dev/null || true
for hook in .githooks/*; do
    [ -f "$hook" ] && write_success "$(basename "$hook") ready"
done

# 3. Initialize submodules
echo -e "\n${CYAN}3️⃣  Initializing git submodules...${NC}"
git submodule update --init --recursive
write_success "Submodules initialized"

# 4. Install Python dev dependencies
echo -e "\n${CYAN}4️⃣  Installing Python dev dependencies...${NC}"
pip install -e ".[dev]"
write_success "Python dependencies installed"

# 5. Install Node dependencies
echo -e "\n${CYAN}5️⃣  Installing Node.js dependencies...${NC}"
if command -v pnpm &> /dev/null; then
    pnpm install
    write_success "Node dependencies installed with pnpm"
elif command -v npm &> /dev/null; then
    npm install
    write_success "Node dependencies installed with npm"
else
    write_warning "npm/pnpm not found — skipping Node dependency installation"
fi

# 6. Environment file
echo -e "\n${CYAN}6️⃣  Environment configuration...${NC}"
if [ -f "apps/tech-mobile/.env.local" ]; then
    write_success ".env.local already configured"
else
    write_warning ".env.local not found — creating with development defaults"
    mkdir -p apps/tech-mobile
    cat > apps/tech-mobile/.env.local << 'EOF'
# Backend API endpoint for development
# This connects to the local backend server (auto-started by git hooks)
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
EOF
    write_success ".env.local created"
fi

# 7. Pre-commit framework (optional)
echo -e "\n${CYAN}7️⃣  Setting up pre-commit framework...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    write_success "pre-commit framework installed"
else
    write_warning "pre-commit not installed (optional) — install with: pip install pre-commit"
fi

# 8. Verify hook installation
echo -e "\n${CYAN}8️⃣  Verifying hook installation...${NC}"
HOOK_PATH=$(git config core.hooksPath)
if [ "$HOOK_PATH" = ".githooks" ]; then
    write_success "Git hooks path: $HOOK_PATH"
else
    write_error "Git hooks path not configured correctly: '$HOOK_PATH'"
    exit 1
fi

# ── Summary ───────────────────────────────────────────────────────────────────
write_header "✅ Setup Complete!"
echo -e ""
echo -e "${CYAN}Git hooks active:${NC}"
echo -e "  ${CYAN}🔧 pre-commit${NC}      — Linting + security checks before commits"
echo -e "  ${CYAN}📝 commit-msg${NC}      — Reserved for future commit message validation"
echo -e "  ${CYAN}🚀 pre-push${NC}        — Tests + bandit + pip-audit before push"
echo -e "  ${CYAN}🔄 post-merge${NC}      — Auto-start backend after pulling changes"
echo -e "  ${CYAN}🌿 post-checkout${NC}   — Verify environment when switching branches"
echo -e ""
echo -e "${CYAN}Common commands:${NC}"
echo -e "  pnpm install                       — Install all dependencies"
echo -e "  pnpm --filter tech-mobile start    — Start Expo dev server"
echo -e "  pre-commit run --all-files         — Run all quality gates now"
echo -e ""
echo -e "${CYAN}Docs:${NC}"
echo -e "  📖 docs/hooks-rehydration.md       — Detailed rehydration guide"
echo -e ""
echo -e "To reinstall hooks at any time: ${YELLOW}git config core.hooksPath .githooks && chmod +x .githooks/*${NC}"
