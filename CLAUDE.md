# Office Hero — Claude Code Instructions

## Session Start (run these first)

Run `/session-start` (or manually):

```bash
cf status          # phase, active tasks file, date
cf next            # recommended next action
```

Then read (in order):

1. **`project-documents/user/tasks/951-tasks.open-work.md`** — the canonical index
   of ALL remaining work. Updated at the end of every session. Start here.
   Work top-to-bottom. Do not skip to a blocked item when a ready item exists above it.

2. **`project-documents/user/project-guides/000-initiatives.md`** — epic-level view.
   Read this when starting a new workstream or making a cross-slice decision.

Supporting detail files (read when implementing the relevant item):

- `project-documents/user/tasks/020-tasks.ux-ci-backlog.md` — UX/CI backlog
  detail (Priority 1–7 all complete except Route reorder UX hint)
- `project-documents/user/architecture/patterns.md` — key architectural patterns
- `project-documents/user/architecture/README.md` — ADR inventory

**After completing any task**, update `951-tasks.open-work.md` immediately —
move the item to `[x]` or remove it, add newly-identified work, update the log.
This is non-negotiable: a stale open-work index is the primary cause of
re-implementing completed work or missing open items at session start.

---

## Phase Gates — enforce before moving forward

### Gate 1: Research (before design, for external dependencies)

Before writing a slice design for any slice that involves:

- An external API (REST, GraphQL, webhooks, OAuth)
- A new infrastructure component (queue, search engine, cache)
- A technology choice with significant switching cost

**Check `project-documents/user/research/` for an existing research artifact.**
If none exists, create one:

1. Spawn an Explore-type subagent to read the external API docs and summarise:
   auth method, rate limits, data model for required entities, pagination, gotchas
2. Write the artifact using the template in `project-documents/user/research/README.md`
3. Name it `NNN-research.{topic}.md` (same number as the target slice)
4. Then proceed to write the slice design

### Gate 2: ADR check (before any architectural decision)

Before proposing an approach that touches system architecture, read the relevant ADRs:

```
project-documents/user/architecture/
  050-arch.hld-office-hero.md    ← full system design
  patterns.md                    ← key patterns in use
  051-adr.web-framework.md       ← FastAPI
  052-adr.routing-engine.md      ← ORS; rate limit implications
  053-adr.tenant-isolation.md    ← RLS; tenant_id required everywhere
  056-adr.backoffice-saga.md     ← Saga + Outbox; no direct API calls
  060-adr.auth.md                ← RS256 JWT; key rotation
  062-adr.rate-limiting.md       ← DB-backed rate limits
```

If your proposed approach contradicts an ADR, either justify the departure and
write a superseding ADR, or change the approach. Do not silently violate decisions.

**When to write a new ADR:** Any decision where:

- The wrong choice is hard to reverse (data model, auth scheme, integration pattern)
- A future implementor would otherwise have to re-derive the reasoning
- The decision constrains how future slices must be implemented

Name new ADRs `0NN-adr.{topic}.md` in the 064–089 range. Add to the README table.

### Gate 3: Slice design (before implementation)

Before implementing any slice:

1. `cf build` — generates focused context from slice design + architecture + tasks
2. Slice design file (`project-documents/user/slices/NNN-slice.*.md`) must exist
   with `status: ready` or `status: in_progress`
3. All dependency slices must have `status: complete` in their task files

Do not start coding without running `cf build` first.

---

## Context Building (for slice work)

```bash
cf build
```

Generates a focused context document from the active slice design, architecture,
and task list. Do not start coding without it.

---

## Code Review (required before every merge)

```bash
sq review code --diff origin/main --cwd c:/Users/jake/Documents/src/github/apps/benj-office-hero
```

Scope to specific files when faster:

```bash
sq review code --files "src/office_hero/**/*.py" --diff origin/main
```

Do not merge without a review that returns APPROVE or APPROVE WITH NITS.
Blocking findings must be fixed first.

---

## Slice Workflow

1. Check `951-tasks.open-work.md` — confirm slice is in "Ready Now" section
2. Check `000-initiatives.md` — understand the epic context
3. Check `research/` — create research artifact if needed (Gate 1)
4. Check ADRs — confirm approach is consistent (Gate 2)
5. Write or verify slice design exists (Gate 3)
6. `cf build` — generate implementation context
7. `git worktree add /tmp/wt-<slice> -b feat/<slice>` — isolated working tree
8. Implement the slice
9. Update slice design `status:` if reality diverged from the design
10. `sq review code --diff origin/main` — review before opening PR
11. Open PR, wait for CI green
12. After merge: update `951-tasks.open-work.md`, tick `003-slices.office-hero.md`

---

## Git Rules (non-negotiable)

- **Always use worktrees** for slice work — branches sharing a working tree collide
  on git staging when parallel agents are active
- **Squash-merge PRs** then `git rebase --onto origin/main <old-base-tip> HEAD`
  for dependent branches (plain rebase replays squashed commits and conflicts)
- **Rate limiter fixtures**: every `app` fixture must save/clear/restore
  `limiter._route_limits` to prevent accumulation across `create_app()` calls in tests
- **Before every commit**: run `git status`, confirm staged set, then
  `sq review code --diff HEAD` or dispatch a code-review subagent

---

## Project Layout

```
src/office_hero/          # FastAPI backend
  api/                    # Routes, schemas, middleware, exception handlers
  core/                   # Domain exceptions, enums, logging
  models/                 # SQLAlchemy models
  repositories/           # DB + in-memory implementations
  services/               # Business logic (one service per slice boundary)
  adapters/               # External adapters (geocoding, routing, back-office)
apps/admin-web/           # React + TypeScript + Vite + Tailwind v3
  src/
    api.ts                # All API client functions and types
    pages/                # Page components
    components/           # Shared UI components
apps/tech-web/            # React + TypeScript + Vite — technician mobile web view
apps/tech-mobile/         # React Native Expo — technician Android app
project-documents/
  user/
    project-guides/       # 000-initiatives.md, spec, slice plan, concept
    slices/               # Slice design docs (one per slice)
    tasks/                # Task breakdowns + 951-tasks.open-work.md
    architecture/         # HLD (050), ADRs (051–089), patterns.md
    research/             # Pre-design research artifacts (create before designing
                          # any slice with external API dependency)
```

---

## Key Technical Patterns

**Exception placement:** Domain exceptions live in `core/exceptions.py`. Route
layer imports from `core`, not from service modules.

**Pydantic schemas:** Use `AwareDatetime` (not `datetime`) for any timestamp that
will be compared against DB values. Use `ConfigDict(extra="forbid")` on all
request schemas.

**RBAC:** Use `dependencies=[Depends(require_permission("resource:action"))]` on
route decorators. Multi-permission endpoints list all requirements.

**Async tests:** Use `asyncio.get_event_loop().run_until_complete()` in sync test
fixtures — not `asyncio.run()`, which closes the global event loop and breaks
other test files in the same session.

**Multi-tenancy:** Every repository method takes `tenant_id` as a required
argument and applies it as a `WHERE` clause. No exceptions. See ADR 053.

**Back-office adapters:** All external CRM/ERP calls go through a class that
implements `BackOfficeAdapter`. No direct HTTP calls to external systems outside
`adapters/back_office/`. All multi-step operations use Saga + Outbox. See ADR 056.
