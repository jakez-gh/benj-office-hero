---
docType: reference
layer: project
audience: [human, ai]
description: ADR — API style choice (REST vs GraphQL)
dateCreated: 20260308
dateUpdated: 20260308
status: decided
---

# ADR 051b: API Style — REST over GraphQL

## Context

Jake asked: *"What do you think about GraphQL vs REST API? Is REST better for
this project? We need an ADR for this."*

Both REST and GraphQL are viable for a field service management API. The choice
affects every client (Tenant Admin web, Technician web, Android app, MCP server),
so it is an early, high-impact decision.

## Candidates

**REST (JSON over HTTP)** — resource-oriented endpoints, standard HTTP verbs,
stateless, widely understood.

**GraphQL** — single endpoint, clients specify exactly what data they need,
strongly typed schema, subscriptions for real-time updates.

## Analysis

### Where GraphQL wins

- **Over-fetching / under-fetching**: Clients request exactly the fields they need.
  Useful when the Tenant Admin dashboard needs a rich Job + Customer + Route view
  in one request.
- **Real-time subscriptions**: GraphQL subscriptions handle live Route updates more
  elegantly than REST polling.
- **Evolving clients**: Adding a new mobile app or MCP tool can query existing types
  without new endpoints.

### Where REST wins for *this* project

- **Simplicity**: FastAPI generates REST with almost no boilerplate. GraphQL requires
  Strawberry or Ariadne, an additional layer to learn and maintain.
- **MCP integration**: The MCP server can be auto-generated from FastAPI's OpenAPI
  spec. GraphQL schema → MCP requires manual mapping.
- **Caching**: REST responses are cache-friendly (CDN, `ETag`, `Cache-Control`).
  GraphQL POST requests are not cacheable by default.
- **Security surface**: GraphQL's flexible queries (deeply nested, N+1 queries) require
  query depth limiting and complexity analysis to prevent abuse. REST endpoints have
  fixed, auditable query shapes — easier to secure and reason about with RBAC.
- **Testing**: REST endpoints are straightforward to unit-test and integration-test.
  GraphQL requires resolver mocking or a running schema.
- **Team / solo context**: Solo developer + AI co-pilot. REST is faster to implement
  correctly and easier for AI agents to reason about (every operation is an endpoint
  with a clear URL, verb, and schema).
- **TDD fit**: REST's fixed request/response shapes map cleanly to repository mocks
  and Pydantic schemas. GraphQL resolvers add a layer that complicates unit testing.

### Real-time concern

The main REST weakness is real-time Route updates for the Technician app. Mitigations:

1. **Polling** (simplest): Technician app polls `GET /routes/{id}` every 30 s.
   Acceptable for initial launch.
2. **WebSocket endpoint** (FastAPI native): Add a single `WS /routes/{id}/live`
   endpoint when polling is insufficient. No need for full GraphQL.
3. **Server-Sent Events** (SSE): Even simpler than WebSockets for one-way push.

GraphQL subscriptions are not needed to solve the real-time problem.

## Decision

**REST** — implemented in FastAPI with a clean resource structure.

Real-time updates handled via polling initially; WebSocket or SSE added as a
targeted enhancement when the need is confirmed by actual customer feedback.

## Isolation Strategy

All HTTP routing lives in `src/office_hero/api/routes/`. The business logic in
`services/` has no knowledge of REST or GraphQL. If a GraphQL layer is ever
desired (e.g. for a future data-heavy analytics dashboard), it can be added as
a parallel interface consuming the same services — without touching any business logic.

## Consequences

- FastAPI + REST is the sole external API surface at launch
- OpenAPI spec is auto-generated — MCP server and external integrators get accurate
  docs for free
- No GraphQL dependency to maintain or secure
- Real-time Route updates require a polling loop in the Technician app at launch;
  WebSocket upgrade is a defined future path if needed
