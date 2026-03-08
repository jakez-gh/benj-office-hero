---
docType: reference
layer: project
audience: [human, ai]
description: Explanation of architectural patterns used in Office Hero
dateCreated: 20260308
dateUpdated: 20260308
---

# Architectural Patterns Reference

This document collects the key software design patterns that the Office Hero
project relies upon. Each pattern is implemented in the codebase via a clear
seam, allowing the implementation to change without affecting business logic.

## Layered Architecture

The application is divided into four layers:

* **API layer** – FastAPI routers and middleware. No business logic.
* **Service layer** – business rules and orchestration. No HTTP or DB imports.
* **Repository layer** – data access via SQLAlchemy. No business logic.
* **Persistence** – PostgreSQL with Row-Level Security.

Services depend on repository *protocols* (ABCs); routers depend on service
interfaces. This separation enforces SOLID principles and simplifies testing.

## Back-Office Adapter Pattern

A protocol defines how Office Hero reads/writes external systems. The default
`NativeAdapter` behaves as the system of record (SoR). Third-party integrations
implement the same protocol. Swapping adapters requires no changes outside
`adapters/back_office/`.

## Saga and Outbox Patterns

Long-running, multi‑step operations that span Office Hero and an external
back‑office system are implemented as sagas. Each step has a compensating
action. The Transactional Outbox pattern guarantees that saga steps are
triggered reliably even if the process crashes.

## Repository Pattern

Each aggregate root (e.g. `Job`, `Tenant`) has a corresponding repository
class and protocol. Services depend on the protocol rather than the concrete
class, enabling mocks for unit tests. Replacement storage engines (e.g. a
NoSQL store) can be supported by providing a new repository implementation.

## Structured Logging

`structlog` is used to produce JSON logs with fields such as `request_id`,
`tenant_id`, and `duration_ms`. The context is automatically preserved across
async calls. An `AuditService` writes security-critical events to a separate
audit table that is append-only.

## Rate Limiting via Database

Rate limits are stored in the `rate_limits` table and loaded by the
`RateLimitManager`. A small cache (1s) allows operators to change the limits via
the admin UI and have them take effect immediately without restarting the
server.

## Layered Security

Security is enforced at multiple layers:

* Transport (HTTPS)
* JWT authentication middleware
* Role/permission decorators on routers
* Service-layer tenant checks
* PostgreSQL Row-Level Security

The evidence for each layer can be found in the corresponding code modules.

---

*Update this file whenever a new pattern is introduced.*
