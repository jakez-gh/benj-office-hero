---
id: 1.2.34
title: Customer Documentation — Comprehensive User Guides
type: slice
parent: 1.2
status: complete
size: small
docType: slice
layer: project
phase: 4
phaseName: sales-and-docs
audience: [human, ai]
description: Nine-file customer documentation suite covering every user role and workflow
dependsOn: [031-slice.ui-improvements.md]
dateCreated: 20260627
dateUpdated: 20260627
---

# Slice 033 — Customer Documentation

## Goal

Give every user role a clear, accurate reference guide they can read on day one and
return to when they hit an edge case. Documentation must cover all shipped features.

## Deliverables

| File | Audience | Topics |
| ---- | -------- | ------ |
| `docs/customer/index.md` | All | Overview, navigation, product summary |
| `docs/customer/getting-started.md` | TenantAdmin | Account setup, first login, inviting users |
| `docs/customer/admin-guide.md` | TenantAdmin, Dispatcher | Full admin manual |
| `docs/customer/dispatch-guide.md` | Dispatcher | 3-option routing, re-routing, emergencies |
| `docs/customer/contracts-guide.md` | TenantAdmin, Sales | Recurring services, auto-generation |
| `docs/customer/technician-guide.md` | Technician | Mobile app, web view, marking stops |
| `docs/customer/integrations-guide.md` | TenantAdmin | ServiceTitan, PestPac, Jobber setup |
| `docs/customer/security-guide.md` | TenantAdmin | Data isolation, audit log, RBAC, HTTPS |
| `docs/customer/faq.md` | All | Common questions + troubleshooting |

## Quality Bar

- Every workflow has numbered steps, not just prose
- Screenshots referenced by path (update as UI evolves)
- Each file can be read standalone (no assumed reading order)
- No internal jargon (Operator/Owner roles not exposed to Tenants)
