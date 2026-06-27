---
id: 1.2.32
title: Sales Materials — Deck + Demo Videos
type: slice
parent: 1.2
status: complete
docType: slice
layer: project
phase: 4
phaseName: sales-and-docs
audience: [human, ai]
description: Static PDF sales presentation (12-slide A4 landscape HTML deck) and demo video infrastructure for sales team use
dependsOn: [031-slice.ui-improvements.md]
dateCreated: 20260627
dateUpdated: 20260627
---

# Slice 032 — Sales Materials

## Goal

Equip sales people with a print-ready PDF deck and recorded demo videos they can use in
prospect conversations, email follow-ups, and live demos.

## Deliverables

| Artifact | Path | Description |
| -------- | ---- | ----------- |
| Sales HTML deck | `docs/sales/sales-deck.html` | 12-slide A4 landscape presentation |
| PDF generator | `scripts/generate-sales-pdf.mjs` | Playwright script → `docs/sales/office-hero-sales-deck.pdf` |
| Demo guide | `docs/sales/DEMO_GUIDE.md` | Instructions for recording/sharing demo videos |
| Demo flow fix | `apps/admin-web/src/e2e/demo-flows.spec.ts` | `networkidle` → `load` for reliability |

## Slide Structure

1. Cover — "Office Hero" + "Dispatch Smarter. Route Faster."
2. The Problem — pain points for small service companies
3. The Solution — three-pillar overview
4. How It Works — five-step workflow diagram
5. Smart Dispatch — dispatch page screenshot
6. Route Management — routes page screenshot
7. Jobs & Customers — jobs/customers screenshot
8. Recurring Contracts — contracts page screenshot
9. Technician Mobile — mobile screenshot
10. Back-Office Integrations — ServiceTitan / PestPac / Jobber
11. Security & Reliability — compliance highlights
12. Get Started — CTA + contact + demo video links

## Demo Videos

The existing `demo-flows.spec.ts` records four scenarios (Demo 1–4) via
`RECORD_VIDEO=1 pnpm playwright test`. The `demo-videos.yml` CI workflow runs
nightly and on every push to `main`, uploading `.webm`/`.mp4` artifacts.

Sales team gets videos by: (a) downloading from the last CI run, or (b) recording
locally following `docs/sales/DEMO_GUIDE.md`.
