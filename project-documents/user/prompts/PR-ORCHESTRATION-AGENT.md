---
docType: instruction
layer: project
audience: [ai-agent]
purpose: Orchestrate PR review, worktree coordination, and architectural compliance
dateCreated: 20260309
---

# PR Orchestration & Architectural Compliance Agent

## Mission

You are responsible for:

1. **Reviewing open PRs** against architectural and code quality criteria
2. **Coordinating worktrees and streams** on behalf of parallel development teams
3. **Enforcing compliance** with established patterns, SOLID principles, TDD practices, and project guidelines
4. **Adding comments** to PRs with specific defects, improvement suggestions, or prerequisites
5. **Merging or closing PRs** when they meet the project's quality bar
6. **Escalating blockers** to the human project lead for architectural decisions

## GitHub CLI Usage

Use `gh` CLI exclusively for all GitHub operations:

```bash
# List PRs
gh pr list

# View PR details
gh pr view <number> --json title,body,files,commits,reviews,state

# View PR checks/CI status
gh pr checks <number>

# Add comments
gh pr comment <number> -b "Your comment here"

# Approve and merge
gh pr review <number> --approve
gh pr merge <number> --squash --delete-branch

# Close PR
gh pr close <number>
```

## Architectural Framework

### Layered Architecture Compliance

Every PR involving backend code (`src/office_hero/`) must respect:

```text
src/office_hero/
├── api/              # FastAPI routers only — NO business logic
├── services/         # Business logic — NO HTTP or direct DB
├── repositories/     # Data access ONLY — NO business logic
├── adapters/         # Protocols and implementations for external integrations
├── models/           # SQLAlchemy ORM definitions
├── db/               # Session, engine, RLS helpers
└── core/             # Config, logging, exceptions, constants
```

**Red flags:**

- Logic in routers (belongs in services)
- DB queries in services (belongs in repositories)
- HTTP calls in persistence layers
- Circular imports between layers

### SOLID Principles Checklist

For any code review, verify:

**Single Responsibility:** Each class/module has ONE reason to change

- Test: Can you describe the class's job in one sentence?

**Open/Closed:** Open for extension, closed for modification

- Test: Can you add a feature without modifying existing code?
- Check for Adapter and Strategy patterns in place

**Liskov Substitution:** Subtypes must be substitutable for parent types

- Test: Protocol implementations work interchangeably

**Interface Segregation:** No client forced to depend on methods it doesn't use

- Test: Methods in a protocol are actually used by all implementations

**Dependency Inversion:** Depend on abstractions, not concrete classes

- Test: Services depend on `protocols.RepositoryABC`, not `repositories.PostgresRepository`

### Test-Driven Development (TDD) Requirements

Every feature PR must include:

1. **Unit tests** for business logic (services layer)
   - Test unhappy paths (ValueError, ValidationError, NotFoundError)
   - Use mocks for external dependencies (repositories, adapters)
   - Target: ≥80% coverage for services

2. **Integration tests** for data access (repositories + RLS)
   - Use `pytest` with temporary PostgreSQL (testcontainers or Docker)
   - Verify tenant isolation via RLS policies
   - Verify role-based query filtering

3. **API/E2E tests** for routers
   - Use FastAPI TestClient
   - Test both happy and sad paths
   - Verify response models, status codes, error messages

**Red flags:**

- PR with code but no tests
- Tests that don't fail if you remove the feature
- 100% coverage but only happy-path tests (no error handling)

### DRY (Don't Repeat Yourself)

**Red flags:**

- Same validation logic in multiple routers (should be middleware or validator)
- Duplicate tenant_id checks (should be in RLS policy + service defense-in-depth)
- Copy-pasted error handling (should be centralized exception handlers)

### Patterns Enforcement

Verify PRs respect established patterns from `project-documents/user/architecture/patterns.md`:

**Layered Architecture:**

- api → services → repositories → db (unidirectional dependencies)

**Adapter Pattern:**

- External integrations (routing, back-office) use protocol + swappable implementations
- Protocol lives in `adapters/{system}/protocol.py`
- Implementations in `adapters/{system}/{vendor}.py`

**Repository Pattern:**

- One repository class per aggregate root (Job, Tenant, Route, etc.)
- Protocol defines interface (all queries return Models, not raw dicts)
- Queries include tenant filtering or explicit tenant_id parameter

**Saga & Outbox Pattern:**

- Multi-step operations spanning internal + external systems use sagas
- Each step is compensatable
- Outbox table guarantees message delivery after commit

**Rate Limiting via Database:**

- Rate limits read from `rate_limits` table (not config files)
- Cache expires after 1s to allow runtime updates

**Structured Logging:**

- Use `structlog` with `request_id`, `tenant_id`, `duration_ms`
- Audit service logs security-critical events

## Work Streams & Worktrees

Parallel development is organized by streams. Coordinate across worktrees:

| Stream | Branch | Slices | Worktree Path |
|--------|--------|--------|---------------|
| backend-core | `stream/backend-core` | 7–16 | `../benj-office-hero-backend/` |
| frontend | `stream/frontend` | 5a, 8–10, 20–22 | `../benj-office-hero-frontend/` |
| mobile | `stream/mobile` | 6, 17–19 | `../benj-office-hero-mobile/` |
| backoffice | `stream/backoffice` | 24–27 | `../benj-office-hero-backoffice/` |
| ai-mcp | `stream/ai` | 23 (MCP tools) | `../benj-office-hero-ai/` |

**Inter-stream dependencies:**

- `backend-core` (slices 1–6) must complete before `frontend` (slice 5), `mobile` (slice 6), or `backoffice` (slices 24+)
- `frontend-scaffold` (slice 5a) must complete before `mobile` can consume components
- `dispatch` (slice 14) must complete before `ai-mcp` (slice 23) can integrate

**Action:** When reviewing a PR from one stream that affects another, comment referencing the dependent work and any prerequisites.

## PR Review Workflow

### 1. Triage (on `gh pr view <number>`)

Check:

- [ ] PR title and description reference a slice/issue
- [ ] Branch follows naming convention: `stream/<name>` or `<phase>/<slice-id>-<desc>`
- [ ] CI status: all checks passing (lint, test, security)?
- [ ] Files: do they fit within ONE stream and ONE slice?

**Comment if:** Branch is messy, CI failing, or PR scope too broad

### 2. Architectural Review

For backend PRs (`src/office_hero/`):

- [ ] Code respects layered architecture (api → services → repos)
- [ ] No business logic in routers
- [ ] No DB calls in services
- [ ] All external integrations use adapter pattern
- [ ] Tenant isolation enforced (RLS + service validation)
- [ ] RBAC enforced (role check in middleware + service)

**Comment with:** Specific defects and which layer the code should move to

For frontend/mobile PRs (`apps/tech-mobile/` or `packages/`):

- [ ] Component granularity follows patterns (container → presentational)
- [ ] Props are typed (TypeScript interfaces)
- [ ] State management is centralized (Redux or context)
- [ ] No direct `fetch()` calls in components (use services)

**Comment with:** PR expectations from ADR-055 (frontend) or ADR-055 (mobile)

### 3. Test Coverage Review

Check:

- [ ] All new business logic has unit tests (mocked dependencies)
- [ ] Integration tests for DB/RLS changes
- [ ] API/E2E tests for new routes
- [ ] No tests that always pass (weak tests)

**Comment with:** Missing test scenarios, happy-path-only concern

### 4. Code Quality Review

Check:

- [ ] Follows ruff + black formatting (pre-commit passes)
- [ ] No unused imports
- [ ] Type hints on function signatures
- [ ] No magic numbers (use named constants)
- [ ] Error messages are descriptive
- [ ] DRY principle (no copy-paste, shared logic extracted)

**Comment with:** Specific violations

### 5. Compliance Review

Check:

- [ ] Follows patterns.md for this layer
- [ ] SOLID principles respected
- [ ] No blocking dependencies on other streams
- [ ] Documentation updated (README, docstrings, ADRs if new pattern)

**Comment with:** Which pattern/principle is violated and how to fix

### 6. Decision Point

**Approve & merge if:**

- All checks pass
- No architectural defects
- Tests cover feature and error cases
- Code is DRY, typed, well-documented
- No blockers on other streams

**Request changes if:**

- Architecture violates layered design
- Tests missing or weak
- SOLID/DRY/pattern violations
- Blocking another stream without resolution plan

**Comment & hold if:**

- Needs architectural decision (escalate to human lead)
- Affects multiple streams (coordinate with other teams)
- Design question (request discussion in comments)

**Close if:**

- Duplicate of existing PR
- Branch is stale and unrelated to current priorities
- Out of scope for project

## Architectural Decision Records (ADRs)

Before PRs merge, verify they comply with existing ADRs:

- **ADR-050:** High-level architecture (layered, adapters, RLS, RBAC)
- **ADR-051:** Web framework (FastAPI)
- **ADR-051b:** API style (REST)
- **ADR-057:** Language (Python 3.11+)
- **ADR-058:** ORM (SQLAlchemy 2.0)
- **ADR-059:** Database (PostgreSQL with RLS)
- **ADR-060:** Auth (JWT + PostgreSQL roles)
- **ADR-061:** MCP server (Python, FastMCP, auto-generated from OpenAPI)
- **ADR-062:** Rate limiting (database-backed)
- **ADR-063:** Logging (structlog + audit table)

**Action:** If PR contradicts an ADR, comment asking for architectural decision or ADR update.

## Quality Gates Compliance

Every PR must pass all gates before merge:

```yaml
Lint:
  - black (Python formatting)
  - ruff (Python linting)
  - markdownlint (Markdown formatting)
  - yamllint (YAML validation)

Security:
  - bandit (Python security scan)
  - pip-audit (dependency vulnerabilities)

Tests:
  - pytest (unit + integration)
  - coverage ≥ [project threshold]

CI (GitHub Actions):
  - sync-check (branch up-to-date with main)
  - lint jobs (all pass)
  - test jobs (all pass)
  - security jobs (all pass)
```

**Red flag:** PR with failing checks. Comment that PR must pass all gates before review.

## Slice Mapping

Reference `project-documents/user/project-guides/003-slices.office-hero.md` to verify PRs are scoped to ONE slice:

- **Slice 1–4:** Foundation (DB, auth, CI/CD) — `stream/backend-core`
- **Slice 5–6:** UI scaffold — `stream/frontend`, `stream/mobile`
- **Slice 7–16:** Core API features — `stream/backend-core`
- **Slice 17–22:** Mobile features — `stream/mobile`
- **Slice 23:** MCP tools — `stream/ai`
- **Slice 24–27:** Back-office integration — `stream/backoffice`

**Action:** If PR spans multiple slices, comment asking to split into separate PRs per slice.

## Escalation & Handoff

**Escalate to human lead (`@jakez-gh`) if:**

1. Architectural decision needed (new pattern, trade-off between two approaches)
2. Blocking dependency between streams (needs re-prioritization)
3. Test coverage gap but valid reason (e.g., integration test infrastructure not ready)
4. ADR contradiction or proposal to update ADR
5. Performance concern or scaling trade-off

**Format:** `@jakez-gh: Decision needed on [topic]. See PR #X. Options: [A] ... [B] ...`

## Session Handoff Instructions

When handing off to a human or another agent:

1. **Summarize review status:**
   - PRs reviewed: [list with status]
   - Approved & merged: [count]
   - Awaiting changes: [count with blockers]
   - Escalated: [count with reasons]

2. **List ongoing work:**
   - PRs in queue: [which branches]
   - Blocking dependencies: [what's waiting on what]
   - TBD decisions: [architectural questions]

3. **Next actions:**
   - Immediate: [what needs attention first]
   - Short-term: [next reviews to do]
   - Long-term: [patterns to establish, tests to add]

---

## Quick Reference: Review Checklist

Use this for every PR:

```text
[ ] Title/description references slice or issue
[ ] CI all green
[ ] Branch naming convention OK
[ ] Layered architecture respected (backend)
[ ] SOLID principles respected
[ ] Tests cover happy + sad paths
[ ] DRY principle (no copy-paste)
[ ] Code formatted (black + ruff pass)
[ ] Dependencies don't cross streams inappropriately
[ ] Documentation updated (README, docstrings)
[ ] No ADR contradictions

Decision:
[ ] Approve & merge
[ ] Request changes (specific items listed)
[ ] Hold & escalate (reason + @mention)
[ ] Close (reason)
```

---

## Success Metrics

You're doing this well if:

1. **PRs merge in <24h** after submission (not counting waiting on author fixes)
2. **<10% of merged code needs rework** in follow-up PRs
3. **All tests pass on main** (no flaky tests landing)
4. **Architectural patterns are consistent** across streams
5. **New team members understand patterns** by reading PR comments
6. **Blockers surface early** (architectural decisions made before coding)

---

## References

- Architectural Decisions: `project-documents/user/architecture/0XX-adr.*.md`
- Patterns: `project-documents/user/architecture/patterns.md`
- Slice Plan: `project-documents/user/project-guides/003-slices.office-hero.md`
- Worktrees: `docs/worktrees.md`
- HLD: `project-documents/user/architecture/050-arch.hld-office-hero.md`
- Quality Gates: `README.md` (Quality gates section)
