---
docType: reference
layer: project
audience: [human, ai]
description: Directory inventory for user/architecture/
dateCreated: 20260308
dateUpdated: 20260308
---

# user/architecture/ — Directory Inventory

Architecture documents for Office Hero. See `file-naming-conventions.md` for
the index range schema.

## What goes here

- **050-099: Project-level architecture** — HLD, project-wide ADRs, governance docs.
  These describe the whole project, not a specific initiative or slice.
- **100-799: Initiative architecture docs** — `nnn-arch.{name}.md` for any new
  architectural initiative that has its own slice plan. Currently unused (Office Hero
  is a single-initiative project).

## What does NOT go here

- Slice plans for initiatives in the 100-799 range belong here as
  `nnn-slices.{name}.md`. **Project-level** slice plan (003) belongs in
  `user/project-guides/`.
- Slice designs (`nnn-slice.*.md`) go in `user/slices/`.
- Task files (`nnn-tasks.*.md`) go in `user/tasks/`.

## Current Files

| File | Type | Description |
| ---- | ---- | ----------- |
| `050-arch.hld-office-hero.md` | HLD | High-Level Design — full system architecture |
| `051-adr.web-framework.md` | ADR | FastAPI chosen over Flask |
| `051b-adr.api-style.md` | ADR | REST chosen over GraphQL |
| `052-adr.routing-engine.md` | ADR | OpenRouteService (ORS) chosen |
| `053-adr.tenant-isolation.md` | ADR | PostgreSQL RLS for tenant isolation |
| `054-adr.hosting.md` | ADR | Fly.io (app) + Neon (DB) |
| `055-adr.frontend.md` | ADR | React (web) + React Native Expo (mobile) |
| `056-adr.backoffice-saga.md` | ADR | Saga + Outbox pattern for back-office risk |
| `057-adr.language.md` | ADR | Python 3.11+ |
| `058-adr.orm.md` | ADR | SQLAlchemy 2.x + Alembic |
| `059-adr.database.md` | ADR | PostgreSQL 15+ |
| `060-adr.auth.md` | ADR | JWT RS256 + bcrypt + refresh tokens |
| `061-adr.mcp-server.md` | ADR | Python MCP SDK + OpenAPI codegen |

## Naming Rules

- HLD: `050-arch.hld-{project}.md`
- ADR: `nnn-adr.{decision-topic}.md` (051-089 range for project-level)
- Variant ADR (same number, different aspect): append letter `b`, `c`
- New initiatives: claim next available base at increment of 10 in 100-799 range
