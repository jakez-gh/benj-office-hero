# DEVLOG

Append-only development log. Newest entries first.
Format: `## YYYYMMDD` date header followed by brief session notes.

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
