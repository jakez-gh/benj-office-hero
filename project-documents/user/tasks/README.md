---
docType: reference
layer: project
audience: [human, ai]
description: Directory inventory for user/tasks/
dateCreated: 20260308
dateUpdated: 20260308
---

# user/tasks/ — Directory Inventory

Task breakdown files for Office Hero. Each file converts a slice design into
granular, actionable tasks (Phase 5). The implementing agent or developer
executes tasks from these files in a single context session.

## What goes here

- `nnn-tasks.{slice-name}.md` — task breakdown for one slice (index matches
  the parent slice design file in `user/slices/`)
- `950-tasks.maintenance.md` — operational/maintenance tasks (not slice-specific)
- Code review task files: `900-review.{component}.md` go in `user/reviews/`

## What does NOT go here

- Slice designs (`nnn-slice.*.md`) — go in `user/slices/`
- Maintenance tasks above 950: follow the 950-999 range
- Architecture docs — go in `user/architecture/`
- Code review files — go in `user/reviews/`

## Current Files

| File | Slice | Status |
| ---- | ----- | ------ |
| `001-tasks.example.md` | — | Example only — delete when creating first real tasks |
| `950-tasks.maintenance.md` | Maintenance | Dev environment setup + recurring ops |

## Task file rules

- Each task: clearly scoped, actionable by junior AI or human dev
- Include success criteria with checkboxes
- Reference the parent slice design in frontmatter (`lld:` field)
- A task file should fit in one context session (< ~350 lines)
- If it overruns: split to `nnn-tasks.{name}-1.md`, `nnn-tasks.{name}-2.md`

See `project-documents/ai-project-guide/project-guides/guide.ai-project.005-task-breakdown.md`
for full guidance.
