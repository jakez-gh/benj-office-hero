# DEVLOG

Append-only development log. Newest entries first.
Format: `## YYYYMMDD` date header followed by brief session notes.

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
- Phase status: Phase 1 ✓, Phase 2 ✓ (pending Jake sign-off), Phase 3 ✓ (pending
  Jake sign-off). Phase 4 (Slice Design) not yet started.

---

## 20260308

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
