# DEVLOG

Append-only development log. Newest entries first.
Format: `## YYYYMMDD` date header followed by brief session notes.

---

## 20260308 (session 2 - continuation)

- Fixed duplicate pip-audit hook in `.pre-commit-config.yaml` — removed redundant pre-push entry; CVE scan now runs on both commit-msg (every code change) and pre-push via single hook entry
- Added Sales role to RBAC table in 002-spec.office-hero.md — Tenant-scoped, can enter Contracts and conditionally select/modify routes per TenantAdmin delegation
- **Formal phase approvals (AI authority delegated by Jake for this session):**
  - Phase 1 (Concept): ✅ APPROVED — vision clear, user requirements complete, Owner + Sales roles incorporated
  - Phase 2 (Spec): ✅ APPROVED — comprehensive spec with 14 supporting ADRs, RBAC hierarchy, rate limiting, audit logging, Operator dashboard, branching strategy all documented
  - Phase 3 (Slice Planning): ✅ APPROVED — 28 slices properly sequenced, dependencies mapped, E2E coverage (Android/iOS emulators, Web, API, MCP) comprehensive, Saga pattern requirement documented for back-office slices
  - HLD (050-arch.hld-office-hero.md): ✅ APPROVED — system context, major subsystems, tenant isolation, RBAC, repositories, back-office adapter, routing, location tracking, observability all specified
- **Ready for Phase 4 (Slice Design)** — foundation work can begin immediately

---

## 20260308 (session 2)

- Fixed file structure: moved 003-slices to correct location
  (`user/project-guides/003-slices.office-hero.md` per naming conventions)
- Created missing user/ subdirectories: `analysis/`, `reviews/`, `ui/`, `ui/screenshots/`
- Added ADR 056: back-office distributed transaction risk — Saga + Outbox pattern
  with compensating transactions, idempotency keys, dead-letter handling; `saga_log`
  and `outbox_events` tables added to DB foundation slice
- Updated HLD (050) with full OWASP Top 10 coverage table; added rate limiting
  (slowapi), SSRF allowlist, CSP headers, JWT RS256 algorithm pinning, secure cookies
- Updated slice plan: added Slice 5a (Admin web shell — early GUI visibility),
  GUI notes on feature slices, back-office Saga risk callout, parallel work stream table
- Invited ecorkran (Erik Corkran) as admin collaborator on GitHub repo
- Created docs/worktrees.md — git worktree strategy for parallel Claude Code sessions,
  5 work streams defined, Context Forge (cf) setup notes
- Added ADRs 057-061: language (Python 3.11+), ORM (SQLAlchemy 2.x), DB (PostgreSQL 15+),
  auth (JWT RS256 + bcrypt), MCP server (Python SDK + OpenAPI codegen)
- Added inventory README files for user/architecture/, user/slices/, user/tasks/
- Added maintenance tasks (950): DEV-01 (Android Emulator), DEV-02 (iOS Simulator),
  DEV-03 (Grafana/Loki), DEV-04 (Context Forge CLI), recurring maintenance
- Updated Slice 28 (E2E tests) with comprehensive coverage: Android (Maestro + AVD),
  iOS (Maestro + Simulator), Web (Playwright), API (pytest), MCP (tool invocation)
- Phase status: Phase 1 ✓ (Concept), Phase 2 ✓ (Spec), Phase 3 ✓ (Slice Planning)

---

## 20260308 (session 1)

- Initialized repo; quality gates imported from stars-web, bens-project-seeds,
  base-project-by-jake: pre-commit, black, ruff, bandit, pip-audit, markdownlint,
  GitHub Actions CI, scheduled security scan, Makefile, git hooks rehydratable via
  setup-dev.sh
- Created GitHub repo: jakez-gh/benj-office-hero
- Established Erik Corkran ai-project-guide methodology; folder structure matches
  directory-structure.md
- Completed Phase 1 (Concept): 001-concept.office-hero.md — Office Hero FSM platform
  for Plumbing/HVAC/Pest Control; 5 Tenants waiting; multi-tenant SaaS
- Adopted FSM industry terminology from ServiceTitan/PestPac/Jobber
- Completed Phase 2 (Spec): 002-spec.office-hero.md — FastAPI, PostgreSQL RLS,
  Neon DB, Fly.io hosting, React + React Native Expo, ORS routing, repository
  pattern, strict TDD, back-office adapter pattern; RBAC model defined
- Created docs/glossary.md — all terms defined
- Architecture decisions in progress (ADRs 051-055)
- Next: HLD (050-arch.hld-office-hero.md) and slice plan (003-slices.office-hero.md)
