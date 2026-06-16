# Office Hero — Claude Code Instructions

## Active Backlog (read this first)

**`project-documents/user/tasks/020-tasks.ux-ci-backlog.md`** is the canonical
backlog for all pending UX fixes, CI/CD automation, E2E tests, and the Dispatch
page redesign. Open it at the start of every session and work top-to-bottom
through unchecked items before picking up new slice work.

## Context Building (start here)

Before implementing any slice, run:

```bash
cf build
```

This generates a focused context document from the active slice design, architecture, and task list. Do not start coding without it.

To check current project state:

```bash
cf status
cf next
```

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
