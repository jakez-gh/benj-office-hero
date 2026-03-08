# 002‑spec.newproject

*(Specification template – second phase of Erik Corkran's AI Project Guide)*

> Fill this out after the concept document is reasonably solid.  The AI
> can help you expand it into requirements, architecture notes, and ADRs.

## Overview

Briefly summarize the project in technical terms.  What will the system do,
and what major components will it have?

## Technology Stack

- Language/runtime: e.g. Python, Node.js, Go
- Frameworks: e.g. FastAPI, React, Next.js
- Database(s): e.g. PostgreSQL, Firestore
- Deployment: e.g. Docker + Kubernetes, serverless
- AI tools: Claude Code, Cursor, etc.

## Architecture

Describe high‑level architecture: services, data flow, third‑party
integrations.  A simple Mermaid/C4 diagram is helpful.

## APIs & Data Model

- List any major public APIs, routes, messages.
- Sketch the principal data entities and relationships.

## Non‑functional Requirements

- Performance targets (e.g. 200 RPS, sub‑500 ms responses)
- Security considerations
- Reliability/SLOs

## Constraints & Dependencies

- Third‑party services, partner APIs, legal constraints, etc.

## ADRs

Use this section to record architecture decision records.  You can
have the AI generate a short ADR by prompting:

> "Write an ADR summarizing why we chose PostgreSQL over MongoDB and
> why we’re deploying on Cloud Run."

---

*Once this spec is in place, go on to slice planning.*
