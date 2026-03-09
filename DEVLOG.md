# DEVLOG

Append-only development log. Newest entries first.
Format: `## YYYYMMDD` date header followed by brief session notes.

---

## 20260309 (session 3)

- **Phase 6 (Implementation) — Slice 4 (Observability) complete:**
  - PR #5 (Slice 1–3 QA hardening) merged to main via squash
  - PR #6 (`phase-6/slice-4-implementation`) rebased onto updated main, force-pushed; CI unblocked
  - phase-6 cleanup commits: fixed `EXPO_PUBLIC_*` env docs, corrected `Makefile` `run` target,
    updated `docs/worktrees.md` with hooks rehydration guidance
  - `stream/backend-core`: SQL injection fix committed — `enable_rls()` now uses `bindparams` with
    `FORBID_LITERAL_BINDS` so raw table names cannot leak into parameterized queries
  - Established tooling directive: use `gh` CLI exclusively for all GitHub operations (no GitKraken MCP)

- **Full PR review pass — all 4 open PRs reviewed:**

  | PR | Branch | Key Findings | Verdict |
  |---|---|---|---|
  | #6 | phase-6/slice-4-implementation | 🔴 `audit_service.py` details dict not `json.dumps()`-serialized before JSONB INSERT; 🟡 `rate_limit_manager.py` global `_cache` breaks test isolation; 🟡 no `test_rate_limit_manager.py`; 🟡 misleading bcrypt docstring in `hash_password()` | Changes requested |
  | #2 | stream/backend-core | 🔴 `auth_service.py` uses raw `bcrypt` (intentionally removed dependency); 🟡 `datetime.utcnow()` deprecated (Python 3.12+) in service and tests | Changes requested |
  | #1 | stream/backoffice | ✅ Saga core clean (StrEnum, dataclasses, Protocol); SagaService compensation/rollback correct; full TDD suite (lifecycle, resilience, idempotency); 🟡 f-string logging (prefer lazy %s); 🟡 `"completed_at": "now"` sentinel should be real ISO timestamp | Approved (minor notes) |
  | #7 | stream/mobile | 🔴 8 session/status markdown docs committed at repo root — must move to `docs/llm/`; 🟡 `catch (err: any)` needs type-safe narrowing; 🟡 missing login-failure error-path test | Changes requested |

---

## 20260308 (session 2 - continuation 3 & 4)

- **Phase 5 (Task Breakdown) Complete for ALL Foundation Slices:**
  - Created comprehensive task breakdowns for all 7 Foundation slices:
    - 004-tasks.python-scaffold.md (Slices 1+1a) — 35 tasks, 7 phases (project structure, CLI, Docker, pre-commit)
    - 005-tasks.database-foundation.md (Slice 2) — 30 tasks, 7 phases (SQLAlchemy, Alembic, RLS, initial tables)
    - 006-tasks.auth-rbac.md (Slice 3) — 32 tasks, 6 phases (auth infrastructure, RBAC, tokens, middleware)
    - 007-tasks.observability.md (Slice 4) — 28 tasks, 6 phases (logging, health checks, security headers, audit, rate limiting)
    - 008-tasks.frontend-scaffold.md (Slice 5) — 25 tasks, 6 phases (pnpm monorepo, shared packages, Vite apps)
    - 009-tasks.admin-web-shell.md (Slice 5a) — 30 tasks, 7 phases (login page, auth context, protected routes, navigation)
    - 010-tasks.mobile-scaffold.md (Slice 6) — 35 tasks, 8 phases (Expo, Android config, location permissions, React Navigation)
  - Total: ~183 granular, actionable tasks across all Foundation slices
  - All follow Phase 5 standard: YAML frontmatter, 6-8 phases, TDD-first ordering, commit checkpoints
  - Established PR-based phase approval workflow: feature branch → PR → self-review with detailed comments → merge
  - PRs reviewed: #1 (lint cleanup), #2 (Slices 2-3 implementation), #3 (mobile Slices 6-19), #4 (Slice 3 task breakdown)
  - All PRs approved and merged to main; agents ready for Phase 6 (Implementation)
  - Mobile agent has already completed Phase 6 work (Slice 6 + Slices 7-19 Expo implementation); awaiting backend API availability for integration testing
  - Backend-core, Frontend, Back-office, and AI/MCP agents have detailed task breakdowns ready to execute in parallel

## 20260308 (session 2 - continuation 2)

- **Phase 4 (Slice Design) Complete:**
  - Created 5 Foundation slice designs: Auth & RBAC (006), Observability (007), Frontend Scaffold (008), Admin Web Shell (009), Mobile Scaffold (010)
  - Slices 1 & 1a, 2 already designed (004, 005) — in_progress
  - All 7 Foundation slices now fully designed with goals, structure, failing tests, dependencies, effort estimates
  - Updated `user/slices/README.md` inventory with all slice files (004-010)
  - Each design is self-contained, detailed enough for task breakdown, follows pragmatic prose style of 004/005
  - Next: Phase 5 (Task Breakdown) begins with Slice 3 (Auth & RBAC) to implement 006-slice design

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
