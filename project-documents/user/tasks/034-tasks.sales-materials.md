---
id: 1.2.32.1
title: Tasks — Sales Materials (Slice 032)
type: tasks
parent: 1.2.32
status: complete
docType: tasks
layer: project
dateCreated: 20260627
dateUpdated: 20260627
---

# Tasks — Sales Materials

## Completed

- [x] Create `docs/sales/` directory
- [x] Write `docs/sales/sales-deck.html` — 12-slide A4 landscape HTML presentation
  - Cover, Problem, Solution, How It Works, 5 feature slides, Security, CTA
  - References existing screenshots from `docs/screenshots/admin-web/`
  - Print-optimized CSS (`@page`, `page-break-after: always`)
- [x] Write `scripts/generate-sales-pdf.mjs` — Playwright PDF generator
  - Opens `docs/sales/sales-deck.html` via file:// URL
  - Outputs `docs/sales/office-hero-sales-deck.pdf` (A4 landscape, no margins)
- [x] Write `docs/sales/DEMO_GUIDE.md` — guide for sales team
  - How to get recorded videos from CI artifacts
  - How to record locally (prerequisites + command)
  - What each demo shows + talking points
- [x] Fix `apps/admin-web/src/e2e/demo-flows.spec.ts`
  - `waitForLoadState('networkidle')` → `'load'` (Vite HMR WebSocket blocks networkidle)
  - Affects Demo 1, Demo 2 navigation calls
