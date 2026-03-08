---
docType: reference
layer: project
audience: [human, ai]
description: Inventory for user/analysis/
dateCreated: 20260308
dateUpdated: 20260308
---

# user/analysis/ — Directory Inventory

This folder contains exploratory documents, data dumps, research notes, and
analysis artifacts that help understand the codebase, domain, or external
systems. It is not part of the production code and may be cleared periodically.

## What goes here

- Ad-hoc investigation write-ups (940-949 range per naming conventions)
- Search results, API contract comparisons, architectural tradeoff studies
- Temporary files produced during research sessions

## What does NOT go here

- Production documentation (specs, ADRs) — those belong in `architecture/`
- Slice designs or task files — those belong in `slices/` and `tasks/`

Keep this directory small; move finished analysis into a more permanent
location (architecture docs, project-guides, or external knowledge repo).
