---
docType: reference
layer: project
audience: [human, ai]
description: Research artifacts directory — pre-design API and technology investigations
dateCreated: 20260617
dateUpdated: 20260617
---

# Research Artifacts

Pre-design investigation documents. Written **before** a slice design is created
whenever the slice involves an external API, a new technology, or a decision with
significant irreversibility.

## When to create a research artifact

**Required** (create before writing the slice design):

- Any slice integrating with an external API (REST, GraphQL, webhooks)
- Any slice adopting a new infrastructure component (queue, cache, search engine)
- Any decision where the wrong choice is hard to reverse after implementation

**Optional** (create if the scope is unclear):

- Slices touching unfamiliar third-party SDKs or libraries
- Performance-sensitive design decisions where profiling data would change the approach

## Naming convention

`NNN-research.{topic}.md` — use the same number as the target slice.

Examples:

- `025-research.servicetitan-api.md` — for Slice 25 (ServiceTitan integration)
- `026-research.pestpac-api.md` — for Slice 26 (PestPac integration)
- `027-research.jobber-api.md` — for Slice 27 (Jobber integration)

## Template

```markdown
---
docType: research
slice: NNN
topic: {api or technology name}
dateCreated: YYYYMMDD
dateUpdated: YYYYMMDD
status: draft | complete
---

# Research: {Topic}

## Goal

One sentence: what decision does this research inform?

## Sources

- Official docs URL
- Changelog / release notes URL
- Known community resources

## Auth & Rate Limits

| Item | Detail |
| ---- | ------ |
| Auth method | OAuth2 / API key / JWT |
| Token lifetime | — |
| Rate limit | N req/min per tenant |
| Quota reset | hourly / daily |
| Sandbox available | yes / no |

## Data Model — Key Entities

Brief description of the entities we need and how they map to Office Hero models.

| External entity | Office Hero entity | Notes |
| --------------- | ------------------ | ----- |
| ... | ... | ... |

## Integration Approach

Recommended approach: polling vs. webhooks, pagination strategy, field mappings.

## Known Gotchas

Anything that would surprise an implementor on day 1 (rate limits, quirky auth flows,
eventually-consistent endpoints, missing sandbox parity, etc.)

## Risks

| Risk | Likelihood | Impact | Mitigation |
| ---- | ---------- | ------ | ---------- |
| ... | low/med/high | low/med/high | ... |

## Decision

Based on this research, the slice design should use: {approach}.
```

## How Claude should use this directory

1. Before designing a slice with an external dependency, check this directory
   for an existing research artifact. If one exists, read it before writing the
   slice design.
2. If no artifact exists, create one via a research subagent (Explore type),
   then write the slice design informed by those findings.
3. After implementation, update the artifact's `status: complete` and note any
   findings that differed from expectations (for future reference).

## Current artifacts

_(none yet — research artifacts will appear here as Slices 25–27 are designed)_
