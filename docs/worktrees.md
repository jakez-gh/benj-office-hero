---
docType: reference
layer: project
audience: [human, ai]
description: Git worktree setup for parallel Claude Code context sessions
dateCreated: 20260308
dateUpdated: 20260308
---

# Parallel Development with Git Worktrees

Git worktrees let you check out multiple branches simultaneously in separate directories.
Each directory can run an independent Claude Code session without interfering with others.

## Why This Matters for Claude Code

Each Claude Code session has its own context window. Long-running sessions can lose
early context. By splitting work into streams mapped to worktrees:

- Each session stays focused on one slice or stream
- File conflicts between parallel sessions are structurally impossible
  (different branches, different directories)
- You can `/compact` one session without losing context in others
- Sessions can be resumed by pointing Claude Code at the worktree directory

## Work Streams

Defined in the slice plan ([003-slices.office-hero.md](../project-documents/user/project-guides/003-slices.office-hero.md)):

| Stream | Branch | Slices | Ready after |
| ------ | ------ | ------ | ----------- |
| `backend-core` | `stream/backend-core` | 7–16 | Foundation 1–4 done |
| `frontend` | `stream/frontend` | 5a, 8–10, 20–22 | Foundation 3, 5 done |
| `mobile` | `stream/mobile` | 6, 17–19 | Frontend scaffold (5) done |
| `backoffice` | `stream/backoffice` | 24–27 | FSM slices 10–12 stable |
| `ai-mcp` | `stream/ai` | 23 | Dispatch (14) done |

## Setup

### First-time: create worktree directories

Run from the repo root once Foundation slices are done:

```bash
# Backend core stream
git worktree add ../benj-office-hero-backend stream/backend-core

# Frontend stream
git worktree add ../benj-office-hero-frontend stream/frontend

# Mobile stream
git worktree add ../benj-office-hero-mobile stream/mobile
```

Each `../benj-office-hero-{name}` directory is a full working copy on its own branch.
Open a separate terminal (and Claude Code session) in each.

### Create stream branches

```bash
git checkout -b stream/backend-core
git push -u origin stream/backend-core

git checkout main
git checkout -b stream/frontend
git push -u origin stream/frontend

# etc.
```

### Start a Claude Code session in a worktree

```bash
cd ../benj-office-hero-frontend
claude  # starts a fresh session scoped to this directory
```

Point Claude Code at the relevant slice design doc as context:

```text
Read project-documents/user/slices/NNN-slice.{name}.md and the task file
project-documents/user/tasks/NNN-tasks.{name}.md. Implement the tasks.
```

## Merge Strategy

When a stream branch is ready to merge:

1. Open a PR from `stream/{name}` → `main`
2. CI runs on the PR branch
3. Review and merge — stream branches are short-lived (one slice or a few related slices)
4. Delete the stream branch after merge; create a new one for the next slice

## Foundation Work Exception

Foundation slices (1–6) **must be done sequentially on `main`** — they are too
interdependent for parallel streams. Do not create worktrees until Foundation is
complete.

## Context Forge (cf)

Context Forge (`cf`) is Erik Corkran's CLI that wraps the ai-project-guide
submodule and adds Claude Code slash commands. Once installed:

```bash
# Install globally (one-time)
npm install -g @context-forge/cli   # or: pnpm add -g @context-forge/cli

# In each worktree/repo
cf init
cf guides install --strategy submodule  # already done — submodule present
cf install-commands                      # installs Claude Code slash commands
```

Check [https://github.com/ecorkran/context-forge](https://github.com/ecorkran/context-forge)
for the current install method. As of this writing `cf` is not yet installed in
this project — run `cf install-commands` once available to unlock slash commands.

## Workspace Notes

- `.pre-commit-config.yaml` is shared across all worktrees (same repo)
- `pyproject.toml` dev deps need `pip install -e ".[dev]"` in each worktree's venv
- The pnpm monorepo (`packages/`, `apps/`) is checked out per worktree — run
  `pnpm install` in each frontend/mobile worktree before starting
- Neon DB branches: use a separate Neon branch per stream for integration tests
  (`NEON_BRANCH=stream-frontend pytest` etc.)
