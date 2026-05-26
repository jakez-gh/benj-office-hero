# Orchestration Playbook

How AI agents (and humans) keep Office Hero moving toward "ready to sell" without anyone holding it all in their head.

This file is the canonical state-of-play and instructions for any future session that picks up this work. Read it first, then `cf status` + `cf next`.

---

## TL;DR — what's happening right now

The project is in a structured agent-orchestration loop driven by Context Forge (CF) + Squadron (SQ).

- **Workers** open and update PRs against the existing stream branches.
- **Reviewers** (fresh agents with no prior context) review each worker PR and post specific findings as PR comments.
- **Workers** respond to review findings with follow-up commits.
- **Loop** continues until a PR is genuinely merge-ready (all CI green, all findings resolved or accepted).

The orchestrator (you, or the human) babysits — dispatches the agents, watches reports, picks the next wave when the current wave merges.

---

## Current state (snapshot — update when it changes)

**Phase:** 6 (Implementation) per CF. Confirmed via `cf status` and `project-documents/user/project-guides/003-slices.office-hero.md`.

**CI:** ✅ Working on `main` (poetry-based, PR #47 merged 2026-05-24). pip-audit is non-blocking; CVEs tracked in issue #48.

**Open PRs in active worker loop** (snapshot at 2026-05-25; refresh with `gh pr list --state open`):

| PR  | Branch                                | What it does                              | Status                          |
|-----|---------------------------------------|-------------------------------------------|---------------------------------|
| #8  | stream/ai                             | MCP server wrapping REST API              | Worker C addressing review      |
| #37 | stream/backoffice                     | Dispatch + Dead-Letter UI to Saga API     | Worker B addressing review      |
| #55 | ci/ui-screenshots                     | UI screenshot CI pipeline                 | Awaiting CI verification        |
| #56 | docs/orchestration-playbook           | This playbook                             | In worker loop                  |
| #57 | phase-4/slices-9-10-12-13-14-design   | Phase-4 design docs for slices 9–14       | Reviewer turn (Wave 2 kick-off) |

**Recently merged** (kept here briefly for traceability):

- #39 (stream/frontend, merged 2026-05-26) — admin shell hardening + hook-driven random-port test orchestration
- #47 (chore/poetry-ci, merged 2026-05-24) — Poetry CI migration

**Open issues:**

- #48 — 17 dependency CVEs (table of fix versions; suggested `poetry update` cascade)

**Backup tags** (created before destructive merges on 2026-05-24):

- `backup/stream-frontend-pre-merge-20260524`
- `backup/stream-backoffice-pre-merge-20260524`
- `backup/stream-ai-pre-merge-20260524`

---

## Work queue — waves to "ready to sell"

Sequence is approximate. Don't start a wave until the previous one has stabilized.

### Wave 1 — Unblock and merge the open PRs ⏳ IN PROGRESS

- [ ] PR #8 — workers + reviewers iterating
- [ ] PR #37 — workers + reviewers iterating
- [x] PR #39 — merged 2026-05-26
- [ ] PR #55 — UI screenshot pipeline merge

**Exit criteria:** all four PRs merged to main; CI green; stale CI-failure issues closed.

### Wave 2 — Backend feature slices to v1 demo path

Spec: `project-documents/user/project-guides/003-slices.office-hero.md`. Each slice needs a design doc before implementation; pattern in `project-documents/user/slices/006-slice.auth-rbac.md`.

- [ ] Slice design docs (Phase 4) for slices 9, 10, 12, 13, 14, 20 — one agent per design doc, parallel
- [ ] Slice 9 — Customer & Location (CRUD + ORS geocoding)
- [ ] Slice 10 — Job (CRUD + status lifecycle + JSONB custom fields)
- [ ] Slice 12 — Vehicle & VehicleCrew (CRUD + crew assignment)
- [ ] Slice 13 — Routing engine integration (ORS adapter + 3 ranked options)
- [ ] Slice 14 — Dispatch & Route management (commit dispatch creates Route + RouteStops)
- [ ] Slice 20 — Admin web — Job entry & customer lookup (UI for slices 9, 10, 13, 14)

**Exit criteria:** a Tenant Admin can log in, create a Customer, create a Job at that Customer's Location, view 3 routing options, dispatch, view the Route. End-to-end happy path passes E2E tests.

### Wave 3 — UI design system + restyling

The admin-web ships with one CSS rule today (see `UI_UX_REPORT_2026-05-24.md` in the worktree root or at `/home/jake/Documents/src/office-hero/UI_UX_REPORT_2026-05-24.md`). This wave fixes that.

- [ ] Decision: Tailwind + shadcn/ui (recommended) vs Mantine vs other
- [ ] Add Tailwind config + base styles
- [ ] Design tokens: colors, type scale, spacing
- [ ] Core components: Card, Table, Button, Input, Form, Alert, EmptyState, Skeleton
- [ ] Sidebar nav with logo (replace pipe-separated top nav)
- [ ] Restyle each page: Login, Jobs, Dispatch, Vehicles, Users
- [ ] Mobile responsive pass
- [ ] Update screenshot baseline (will happen automatically via the ui-screenshots workflow after PR #55 merges)

**Exit criteria:** UI is presentable to a real plumbing/HVAC business owner without embarrassment. Compare against Jobber screenshots — should be in the same league.

### Wave 4 — Multi-tenant onboarding

- [ ] Slice 7 — Tenant management (Operator CRUD for Tenants)
- [ ] Slice 7a — Operator observability dashboard
- [ ] Slice 8 — User management (TenantAdmin CRUD)
- [ ] Tenant invitation email flow
- [ ] First-time-setup wizard for new Tenants

**Exit criteria:** Jake can onboard a new Tenant in under 10 minutes without manual DB work.

### Wave 5 — Production readiness

- [ ] Address issue #48 (17 dependency CVEs)
- [ ] Production deploy on Fly.io (per ADR 054)
- [ ] Custom domain + TLS
- [ ] Real DB on Neon (per ADR 059)
- [ ] Backups + restore-from-backup verified
- [ ] Status page (uptime.com or similar)
- [ ] Production logging/alerting (Grafana/Loki per maintenance task DEV-03)

**Exit criteria:** Office Hero runs at production-grade reliability on a real domain.

### Wave 6 — Commercial layer

- [ ] Stripe integration (Stripe Billing for subscription tiers)
- [ ] Free trial logic (14 days, no card required)
- [ ] Tenant-facing billing portal
- [ ] Pricing page on marketing site
- [ ] Terms of service + privacy policy
- [ ] Customer support entry point (email, intercom, or similar)
- [ ] Basic support docs (how to add a job, dispatch, etc.)

**Exit criteria:** A new prospect can sign up, see pricing, start a trial, and pay — without touching anyone at Office Hero.

### Wave 7 — First sale

- [ ] Demo to one of the 5 waiting Tenants (concept doc lists they exist)
- [ ] Pricing decision finalized
- [ ] First paid Tenant onboarded
- [ ] Case study / testimonial captured

**Exit criteria:** $99+ MRR. Now you can iterate based on real customer feedback.

---

## Orchestration pattern

### The worker → reviewer → merge loop

```
┌─────────────────┐
│  Open PR exists │
│  (or new slice) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Worker agent    │  Receives: PR # or slice ID + review findings + ADR refs
│ (background)    │  Does: read files, fix issues, run tests, push commits, comment
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CI runs         │  Watched via Monitor or gh pr checks --watch
└────────┬────────┘
         │
         ▼  (green)
┌─────────────────┐
│ Reviewer agent  │  Fresh — no prior context. Receives: PR # only.
│ (background)    │  Does: full code review, posts comment with findings.
└────────┬────────┘
         │
         ▼
   Findings empty? ──No──► Loop back to Worker agent with new findings
         │ Yes
         ▼
┌─────────────────┐
│ Merge           │  Orchestrator merges via `gh pr merge `{N}` --squash --delete-branch`
└─────────────────┘
```

### Agent dispatch templates

#### Worker template

> You are a worker agent on the Office Hero project (jakez-gh/benj-office-hero).
>
> **Working directory:** `<path to worktree for the branch>`
>
> **Project context tools:** `cf status`, `cf next`, `cf build` (Office Hero is Phase 6, registered with CF). `gh` is authenticated. Backup tag at `backup/<branch>-pre-<date>`.
>
> **Findings to address:** [paste relevant section of PR review comment]
>
> **Quality bar before pushing:**
>
> - `poetry install --with dev --no-interaction` succeeds
> - `poetry run pytest -q` passes
> - `poetry run pre-commit run --all-files` passes
> - `pnpm -r --filter !tech-mobile run test` passes
> - `gh pr checks {N}` is all green (substitute the PR number)
>
> **Workflow:** read PR review → read affected files → fix in priority order → run quality checks → commit semantically → push to existing branch → comment on PR addressing each finding.
>
> **DO NOT merge the PR.** A reviewer agent will check first.
>
> Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
>
> Report back with: commits pushed, CI status, per-finding resolution.

#### Reviewer template

> You are a code reviewer with no prior context on this conversation.
>
> Review PR #`{N}` on jakez-gh/benj-office-hero. The repo is at `/home/jake/Documents/src/office-hero/benj-office-hero/main/`.
>
> Read the actual code changes: `gh pr view {N} --json files` and `git diff origin/main..origin/<branch>` (from the main worktree, substituting the PR number and branch).
>
> Assess: code quality, security, completeness, test coverage, ADR compliance (ADRs in `project-documents/user/architecture/`), separation of concerns, error handling.
>
> Output a PR-comment-ready review (under 800 words):
>
> - **Verdict:** APPROVE / APPROVE WITH NITS / REQUEST CHANGES / BLOCK
> - **Top issues** (numbered, severity 🔴 / 🟡 / 🟢)
> - **What's done well** (1–3 bullets)
> - **Specific files to look at** (with line numbers)
> - **Recommended next steps**
>
> Save the review to `/tmp/pr{N}-review-<timestamp>.md` and post it as a PR comment with `gh pr comment {N} --body-file <path>`.

### Slice design template (Phase 4 work in Wave 2)

> You are writing a slice design document for Slice `{N}` of the Office Hero project.
>
> Read the slice description in `project-documents/user/project-guides/003-slices.office-hero.md` for Slice `{N}`.
>
> Read the existing design doc pattern in `project-documents/user/slices/006-slice.auth-rbac.md` and match its structure.
>
> Write a new slice design doc at `project-documents/user/slices/{NNN}-slice.{name}.md`. Include: goals, structure (files to create), failing tests (TDD list), dependencies, effort estimate.
>
> Reference relevant ADRs in `project-documents/user/architecture/`.
>
> Commit on a `phase-4/slice-{N}-design` branch and open a PR.

---

## Scheduled remote orchestrator

A claude.ai routine is configured to run this orchestration loop once per hour, independent of any local session.

- **Routine ID:** `trig_016kxXhmZQhycdUDtFXdnzLS`
- **Dashboard:** <https://claude.ai/code/routines/trig_016kxXhmZQhycdUDtFXdnzLS>
- **Cadence:** `17 * * * *` UTC (every hour at minute :17)
- **Model:** `claude-opus-4-7`
- **Source:** `jakez-gh/benj-office-hero` (clean clone each tick)
- **Per-tick budget:** at most ONE worker dispatch + ONE reviewer dispatch + ONE merge
- **Tick log:** `orchestration-tick-log.md` at the repo root, committed periodically on `chore/tick-log`

> **Current status (2026-05-25): DISABLED.** The routine was auto-disabled by claude.ai with
> `ended_reason: auto_disabled_repo_access` — the cloud agent could not authenticate against
> this private repo. Until the Claude Code GitHub App is installed for `jakez-gh/benj-office-hero`
> and the routine is re-enabled via the dashboard above, **the worker → reviewer → merge loop
> only runs from local sessions** (humans dispatching workers/reviewers by hand or via local
> Squadron). Treat any reference to "hourly automation" in this file as aspirational until the
> dashboard shows the routine as Active again.

If the routine is making bad decisions, update or pause it via the dashboard. If the orchestration logic in this file changes meaningfully, also update the routine's embedded prompt — the routine carries a fallback copy of the priority order in case this file isn't on `main` yet at tick time.

---

## How to resume in a new session

Any future agent or human picks up like this:

1. **Read this file** (`docs/ORCHESTRATION.md`) first.
2. **Run `cf status`** in the main worktree to see CF's view of project state.
3. **Run `gh pr list --state open --json number,title,headRefName`** to see active PRs.
4. **Read the "Current state" section above.** If the snapshot is stale (PRs merged, new wave started), update it.
5. **Identify the active wave** from the work queue. Pick up wherever the previous session stopped.
6. **For active PRs in the worker loop:** check `gh pr view {N} --comments` (substituting the PR number) to see whether a worker or reviewer ran last. If worker last, dispatch reviewer. If reviewer last (with findings), dispatch worker.
7. **For waves not started yet:** read the wave's exit criteria, decompose into discrete tasks, dispatch workers.

---

## Definition of "ready to sell"

The project is ready to sell when:

1. ✅ A new Tenant can sign up at a public URL without contacting anyone
2. ✅ The free trial path works end-to-end (sign up → dispatch a job → see route → invite a technician)
3. ✅ Paid conversion via Stripe works
4. ✅ Terms of Service, Privacy Policy, and basic support docs are linked from the marketing site
5. ✅ The product handles real-world dispatch use cases for at least one industry (plumbing, HVAC, or pest control) without crashes
6. ✅ At least one paying Tenant has used it for 7 consecutive days
7. ✅ Basic operational alarms (uptime, error rate, payment failures) page Jake if they trip

All seven must hold simultaneously. Until then: not ready to sell.

---

## Notes for the orchestrator

- **Don't merge worker PRs without a fresh reviewer.** The whole point of the loop is independent verification.
- **Don't let workers operate on `main` directly.** All work happens on the existing stream branches or new slice branches.
- **Don't dispatch a worker without a clear list of findings.** Vague prompts produce vague work.
- **Trust the CF/SQ methodology.** Office Hero already follows it (Phase 1–6, slice plans, ADRs). Stay in pattern; don't invent parallel structures.
- **When stuck, use `cf next` and read the ADRs.** The project has answers — most of them.
- **Match every code commit with the `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` footer.** Traceability.

This document is intentionally living. Update it every time a wave moves forward.
