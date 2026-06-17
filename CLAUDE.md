# Office Hero — Claude Code Instructions

## Session Start (run these first)

Run `/session-start` (or manually):

```bash
cf status          # phase, active tasks file, date
cf next            # recommended next action
```

Then read:

**`project-documents/user/tasks/951-tasks.open-work.md`** — the canonical index
of ALL remaining work. Updated at the end of every session. Start here. Work
top-to-bottom. Do not skip to a blocked item when a ready item exists above it.

Supporting detail files (read when implementing the relevant item):

- `project-documents/user/tasks/020-tasks.ux-ci-backlog.md` — UX/CI backlog
  detail (Priority 1–6 complete; 1 open item: Route reorder UX hint)
- `project-documents/user/tasks/010-tasks.mobile-scaffold.md` — Slice 6 detail
- `project-documents/user/slices/007a-slice.operator-dashboard.md` — Slice 7a
  design (not yet written; write it before implementing)

**After completing any task**, update `951-tasks.open-work.md` — move the item
to `[x]` or remove it, and add any newly-identified work.

## Context Building (for slice work)

Before implementing any slice, run:

```bash
cf build
```

This generates a focused context document from the active slice design, architecture, and task list. Do not start coding without it.

## Code Review (required before every merge)

Use sq to review PRs before merging:

```bash
sq review code --diff origin/main --cwd c:/Users/jake/Documents/src/github/apps/benj-office-hero
```

Or scope to specific files:

```bash
sq review code --files "src/office_hero/**/*.py" --diff origin/main
```

Do not merge a PR without a review that returns APPROVE or APPROVE WITH NITS. Blocking findings must be fixed first.

## Slice Workflow

1. `cf next` — identify the next slice to work on
2. `cf build` — generate implementation context
3. `git worktree add /tmp/wt-<slice> -b feat/<slice>` — isolated working tree
4. Implement the slice
5. `sq review code --diff origin/main` — review before opening PR
6. Open PR, wait for CI green
7. After merge: `cf check` to verify frontmatter is clean

## Git Rules (non-negotiable)

- **Always use worktrees** for slice work — branches sharing a working tree collide on git staging when parallel agents are active
- **Squash-merge PRs** then `git rebase --onto origin/main <old-base-tip> HEAD` for dependent branches (plain rebase replays squashed commits and conflicts)
- **Rate limiter fixtures**: every `app` fixture must save/clear/restore `limiter._route_limits` to prevent accumulation across `create_app()` calls in tests
- **Before every commit**: run `git status`, confirm staged set, then `sq review code --diff HEAD` or dispatch a code-review subagent

## Project Layout

```
src/office_hero/          # FastAPI backend
  api/                    # Routes, schemas, middleware, exception handlers
  core/                   # Domain exceptions, enums, logging
  models/                 # SQLAlchemy models
  repositories/           # DB + in-memory implementations
  services/               # Business logic (one service per slice boundary)
  adapters/               # External adapters (geocoding, routing)
apps/admin-web/           # React + TypeScript + Vite + Tailwind v3
  src/
    api.ts                # All API client functions and types
    pages/                # Page components
    components/           # Shared UI components
project-documents/
  user/
    project-guides/       # Spec, slice plan, architecture
    slices/               # Slice design docs (one per slice)
    tasks/                # Task breakdowns
    architecture/         # HLD and ADRs
```

## Key Technical Patterns

**Exception placement:** Domain exceptions live in `core/exceptions.py`. Route layer imports from `core`, not from service modules.

**Pydantic schemas:** Use `AwareDatetime` (not `datetime`) for any timestamp that will be compared against DB values. Use `ConfigDict(extra="forbid")` on all request schemas.

**RBAC:** Use `dependencies=[Depends(require_permission("resource:action"))]` on route decorators. Multi-permission endpoints list all requirements.

**Async tests:** Use `asyncio.get_event_loop().run_until_complete()` in sync test fixtures — not `asyncio.run()`, which closes the global event loop and breaks other test files in the same session.
