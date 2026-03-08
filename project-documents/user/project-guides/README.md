---
docType: reference
layer: project
audience: [human, ai]
description: Inventory for user/project-guides/
dateCreated: 20260308
dateUpdated: 20260308
---

# user/project-guides/ — Directory Inventory

Contains project-specific versions or customisations of the AI project guide itself
and the key planning documents (concepts, specs, slice plans) for this project.

## What goes here

- `001-concept.{project}.md` (Phase 1 concept documents)
- `002-spec.{project}.md` (Phase 2 specification documents)
- `003-slices.{project}.md` (Phase 3 slice plans for entire project)
- Any project-level guide customizations that extend or override the framework
  guides in `project-documents/ai-project-guide/project-guides/`.

## What does NOT go here

- Slice design files (`user/slices/`) or task breakdowns (`user/tasks/`)
- Architecture documents or ADRs (`user/architecture/`)
- Frontend/mobile source code

This directory is the source of truth for high-level planning artifacts that are
unique to this project.
