---
layer: project
phase: 1
phaseName: concept
guideRole: primary
audience: [human, ai]
description: Concept for Office Hero
dependsOn: []
dateCreated: 20260308
dateUpdated: 20260308
status: review
---

# Office Hero

## Overview

A multi-tenant field service management (FSM) platform for small service companies
in the plumbing, HVAC, and pest control industries — enabling Job intake,
intelligent Dispatch, and real-time truck routing.

---

## User-Provided Concept

> *This section preserves the Operator's original vision verbatim. Do not edit.*

This will be a tool used by Plumbers, Pest Control and HVAC professionals to:

- add new contracts to their back office systems.
- automatically route truck for new contracts or adapting to real-world events like
  sick-days or emergencies.
- manually adjust truck routes.

Goals: connection with customer backend systems, starting with the easiest and most
common. Follow SOLID and DRY. Religious following of TDD and other quality control
techniques. Automatically route trucks for new contracts.

Requirements: determine what fields we require from contracts and a common vocabulary.
As an option we will first store the information in our backend system but later we
will connect to the customer's current system to integrate seamlessly.
Allow a customer to enter a new contract into our backend system.

Risks: we need to be careful to not allow our customers to see each others information
or my information for managing the full system. Customers should only be able to see
their own data. Quality and security need to be addressed before anything else.

5 customers are already waiting for the product.

---

## Terminology

Industry-standard terms borrowed from PestPac, ServiceTitan, and Jobber where possible.

| Term | Definition |
| ---- | ---------- |
| **Operator** | Jake + any internal staff running the platform (our term — not visible to Tenants) |
| **Owner** | Internal super-admin with full rights across all Tenants and Operators; only another Owner can assign this role. |
| **Tenant** | A service company subscribed to Office Hero — the plumber, HVAC co., or pest control co. (our SaaS term; in the UI this may appear as "Company") |
| **Tenant Admin** | Owner or office manager at a Tenant; configures the account, manages their team |
| **Technician** | A field worker employed by a Tenant who travels to and performs Jobs (universal FSM term) |
| **Customer** | The end customer of a Tenant — the homeowner or business getting the work done. They never interact with Office Hero directly. (ServiceTitan/Jobber standard) |
| **Job** | A discrete service visit to be performed for a Customer at a Location. The core operational record. (ServiceTitan/Jobber/Housecall Pro standard; PestPac: "Service Order") |
| **Contract** | A recurring service agreement between a Tenant and a Customer that generates Jobs on a schedule (e.g. quarterly pest control plan). (PestPac standard) |
| **Location** | A service address associated with a Customer. A Customer may have multiple Locations. (ServiceTitan standard) |
| **Route** | The ordered sequence of Jobs assigned to one Vehicle/Technician for a day (universal FSM term) |
| **Vehicle** | The truck or van assigned to Technician(s) for a Route |
| **Dispatch** | The act of assigning and routing Jobs to Vehicles/Technicians (universal FSM term) |

---

## Refined Concept

### Problem & Motivation

Small field service companies (plumbing, HVAC, pest control) lack affordable software
for managing Jobs and routing their Technicians efficiently. They rely on phone calls,
spreadsheets, or expensive enterprise FSM tools (ServiceTitan, PestPac). Office Hero
provides a focused, accessible alternative. Five Tenants are waiting for the product —
commercial launch is the near-term goal.

### Target Users

**Primary (daily users):**

- **Tenant Admin** — enters or reviews Jobs, reviews and approves Routes, handles
  day-of exceptions (Technician sick, emergency added, Customer cancels).- **Tenant Sales** â€” a Tenant employee granted permission by the Tenant Admin to
  enter new Jobs/Contracts and to propose or manually adjust Routes for their Crew.- **Technician** — may enter a Job in the field; receives their daily Route and
  acknowledges it via their mobile browser.

**Secondary (platform oversight):**

- **Owner** — super-admin with god-level permissions over the entire platform. Manages Operators, billing, and may impersonate Tenants for troubleshooting.

**Never a user:**

- **Customer** — the homeowner or business receiving the service. No direct
  interaction with Office Hero.

### Solution Approach

A web-based, multi-tenant SaaS platform. Each Tenant is strictly isolated — no
Tenant can see another Tenant's data or Operator-level views.

**Core workflow:**

1. A Tenant Admin or Technician enters a new Job (Customer, Location, service type,
   scheduling window, notes).
2. The platform presents **three routing options** for the Job, with a recommended
   best option pre-selected, based on current Vehicle positions and existing Route load.
3. The Tenant Admin selects one of the three options, or manually enters a fourth
   custom option.
4. Routes update dynamically when day-of events occur (Technician sick, Customer
   cancels, emergency Job added).

**Real-time awareness:**

- Technician Vehicle location is tracked via the mobile browser Geolocation API
  so the routing engine always has current positions. No native app required at launch.

**Industry-specific fields:**

- Plumbing, HVAC, and pest control share the core Job model.
- Industry-specific fields (e.g. permit numbers for plumbing, chemical usage records
  for pest control) are handled via configurable Job field templates per Tenant.

**Integration path:**

- Phase 1: Office Hero is the system of record (all data stored internally).
- Phase 2+: Optional integration with existing Tenant back-office systems,
  starting with the most common and easiest to connect.

### Initial Technical Direction

- **Language:** Python 3.11+
- **Deployment:** Free-tier cloud hosting at launch (Railway, Render, or Fly.io)
- **Database:** PostgreSQL with row-level Tenant isolation
- **Routing engine:** TBD — OpenRouteService (fully free/open-source) preferred
  over Google Maps to avoid API costs
- **Location tracking:** Mobile browser Geolocation API (no native app at launch)
- **Frontend:** TBD in Phase 2

### Development Approach

All design patterns used in this document (layered architecture, adapter pattern, saga, outbox, etc.) are detailed in `project-documents/user/architecture/patterns.md` so developers can consult them when implementing.

All design patterns used in this document (layered architecture, adapter
pattern, saga, outbox, back-office adapters, etc.) are documented in the
project's patterns reference so developers can understand and reuse them.

- **TDD** throughout — tests written before implementation
- **SOLID and DRY** enforced via linter rules and AI-assisted code review
- **Security first** — Tenant isolation is a hard requirement, not a backlog item
- **Vertical slices** — each slice delivers working, tested, deployable functionality
- **Solo + AI** per the methodology in `docs/human-steps.md`
- **Quality gates** already in place (pre-commit, CI, daily CVE scan)
