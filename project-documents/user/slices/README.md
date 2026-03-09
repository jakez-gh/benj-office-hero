---
docType: reference
layer: project
audience: [human, ai]
description: Directory inventory for user/slices/
dateCreated: 20260308
dateUpdated: 20260308
---

# user/slices/ — Directory Inventory

Slice design documents (Low-Level Designs) for Office Hero. Each file describes
the detailed design for one vertical slice before implementation begins (Phase 4).

## What goes here

- `nnn-slice.{slice-name}.md` — one file per slice
- Index `nnn` matches the slice's number in the slice plan (`003-slices.office-hero.md`)
  AND matches the corresponding task file in `user/tasks/`
- Foundation slices (1-6) and Feature slices (7-23) share the 100-band index space
  (100 = Slice 1, 101 = Slice 2, etc.) — see `file-naming-conventions.md`

## What does NOT go here

- The overall slice plan (`003-slices.office-hero.md`) is in `user/project-guides/`
- Task files (`nnn-tasks.*.md`) are in `user/tasks/`
- Architecture docs and ADRs are in `user/architecture/`
- UI mockups and screenshots go in `user/ui/` and `user/ui/screenshots/`

## Current Files

| File | Slice | Status |
| ---- | ----- | ------ |
| `001-slice.example.md` | — | Example only (reference) |
| `004-slice.python-scaffold.md` | 1 + 1a | in_progress |
| `005-slice.database-foundation.md` | 2 | in_progress |
| `006-slice.auth-rbac.md` | 3 | not_started |
| `007-slice.observability.md` | 4 | not_started |
| `008-slice.frontend-scaffold.md` | 5 | not_started |
| `009-slice.admin-web-shell.md` | 5a | not_started |
| `010-slice.mobile-scaffold.md` | 6 | not_started |

## When to create a slice file

Create a slice design (Phase 4) when:

1. The slice is next in implementation order
2. All its dependencies are complete or in progress
3. A new Claude Code context session is about to start implementation

## Slice design file template

See `project-documents/ai-project-guide/project-guides/guide.ai-project.004-slice-design.md`
for the full template and instructions.
