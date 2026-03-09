#!/usr/bin/env bash
# Setup script for Office Hero development environment
# Run this once after cloning: bash scripts/setup-dev.sh

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

write_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
}

write_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

write_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

write_error() {
    echo -e "${RED}❌ $1${NC}"
}

write_header "Office Hero Mobile Development Setup"

# 1. Configure Git hooks
echo ""
echo -e "${CYAN}1️⃣  Configuring Git hooks...${NC}"
git config core.hooksPath .githooks
if [ $? -eq 0 ]; then
    write_success "Git hooks path configured (.githooks)"
else
    write_error "Failed to configure git hooks"
    exit 1
fi

# 2. Make hooks executable
echo ""
echo -e "${CYAN}2️⃣  Ensuring hook scripts are executable...${NC}"
chmod +x .githooks/* 2>/dev/null || true
for hook in .githooks/*; do
    if [ -f "$hook" ]; then
        write_success "$(basename $hook) ready"
    fi
done

# 3. Install Node dependencies
echo ""
echo -e "${CYAN}3️⃣  Installing Node.js dependencies...${NC}"
if command -v pnpm &> /dev/null; then
    pnpm install
    write_success "Dependencies installed with pnpm"
elif command -v npm &> /dev/null; then
    npm install
    write_success "Dependencies installed with npm"
else
    write_warning "npm/pnpm not found - skipping Node dependency installation"
fi

# 4. Backend setup info
echo ""
echo -e "${CYAN}4️⃣  Backend configuration...${NC}"
echo -e "${CYAN}The backend will start automatically via git hooks when you:${NC}"
echo -e "  ${CYAN}•${NC} Pull changes: post-merge hook auto-starts backend if needed"
echo -e "  ${CYAN}•${NC} Checkout branches: post-checkout hook verifies environment"
write_success "Backend auto-startup configured"

# 5. Environment file
echo ""
echo -e "${CYAN}5️⃣  Environment configuration...${NC}"
if [ -f "apps/tech-mobile/.env.local" ]; then
    write_success ".env.local already configured"
else
    write_warning ".env.local not found - creating with development defaults"
    cat > apps/tech-mobile/.env.local << EOF
# Backend API endpoint for development
# This connects to the local backend server (auto-started by git hooks)
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
EOF
    write_success ".env.local created"
fi

# 6. Pre-commit setup
echo ""
echo -e "${CYAN}6️⃣  Setting up commit hooks...${NC}"
if command -v pre-commit &> /dev/null; then
    pre-commit install
    write_success "pre-commit framework installed"
else
    write_warning "pre-commit not installed (optional)"
    echo -e "  ${YELLOW}Install with: pip install pre-commit${NC}"
fi

# Summary
write_header "✅ Setup Complete!"
echo ""
echo -e "${CYAN}Available commands:${NC}"
echo -e "  ${CYAN}•${NC} pnpm install              - Install all dependencies"
echo -e "  ${CYAN}•${NC} pnpm --filter tech-mobile start  - Start Expo dev server"
echo -e "  ${CYAN}•${NC} git pull                  - Backend auto-starts via post-merge hook"
echo ""
echo -e "${CYAN}Git hooks configured:${NC}"
echo -e "  ${CYAN}🔧 pre-commit${NC}      - Linting + security checks before commits"
echo -e "  ${CYAN}🔄 post-merge${NC}      - Auto-start backend after pulling changes"
echo -e "  ${CYAN}🌿 post-checkout${NC}   - Verify environment when switching branches"
echo ""
echo -e "${CYAN}Documentation:${NC}"
echo -e "  ${CYAN}📖 See SETUP.md for detailed rehydration instructions${NC}"
echo ""
