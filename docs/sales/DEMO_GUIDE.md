# Office Hero — Demo Video Guide

**Audience:** Sales team, account managers  
**Updated:** 2026-06-27

---

## What the demos show

Four Playwright recordings walk through real end-to-end workflows against a live backend.
Each demo seeds its own isolated tenant — no shared state between runs.

| Demo | Duration (approx.) | What it covers |
|------|-------------------|----------------|
| **Demo 1 — Jobs & Dispatch** | ~3 min | Jobs list → filter by status → Routes page → Vehicles page → Dispatch form (emergency job) |
| **Demo 2 — Contracts lifecycle** | ~2 min | Customers page → Contracts page → Generated jobs from contract |
| **Demo 3 — Route management** | ~2 min | Route list → start route via API → stop progression (arrived → complete) |
| **Demo 4 — Tenant admin** | ~2 min | Tenants page → create new tenant → Operator Dashboard |

---

## Option A — Download from CI (easiest)

Every push to `main` triggers the `demo-videos` GitHub Actions workflow (nightly at 02:00 UTC).
Videos are uploaded as artifacts named `demo-videos-<SHA>`.

1. Go to **github.com/jakez-gh/benj-office-hero/actions/workflows/demo-videos.yml**
2. Click the latest successful run
3. Under **Artifacts**, download **demo-videos-&lt;SHA&gt;**
4. Unzip — you'll find `.webm` files, one per demo

> **Tip:** `.webm` plays natively in Chrome and Firefox. To convert to `.mp4` for wider
> compatibility: `ffmpeg -i input.webm -c:v libx264 -c:a aac output.mp4`

---

## Option B — Record locally

Use this when you want fresh recordings against the latest code or a specific dataset.

### Prerequisites

```powershell
# 1. Start the backend with test auth enabled
$env:OFFICE_HERO_TEST_AUTH = "1"
poetry run uvicorn office_hero.main:app --host 127.0.0.1 --port 8000
```

```powershell
# 2. In a second terminal — record the demos (from repo root)
$env:RECORD_VIDEO = "1"
$env:DEMO_BACKEND = "1"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
cd apps/admin-web
npx playwright test src/e2e/demo-flows.spec.ts --project=chromium --reporter=line
```

Videos are written to `apps/admin-web/test-results/` as `.webm` files.

### One-liner (Git Bash / WSL)

```bash
RECORD_VIDEO=1 DEMO_BACKEND=1 VITE_API_BASE_URL=http://127.0.0.1:8000 \
  pnpm --filter admin-web exec playwright test src/e2e/demo-flows.spec.ts \
  --project=chromium --reporter=line
```

---

## Generating the PDF sales deck

```bash
# From repo root — requires Playwright Chromium installed in apps/admin-web
node scripts/generate-sales-pdf.mjs
# Output: docs/sales/office-hero-sales-deck.pdf
```

Open `docs/sales/sales-deck.html` directly in Chrome for a live preview.

---

## Sales talking points per demo

### Demo 1 — Jobs & Dispatch

- **Open with:** "Here's the dispatcher's view on a typical morning…"
- Point out the status filter (pending/scheduled) — shows only what needs action
- Highlight the dispatch form's search field — type "Emergency" and watch the list narrow
- Note the vehicle auto-populates based on available crews

### Demo 2 — Contracts lifecycle

- **Open with:** "Riverside Cleaning Co has a monthly contract — here's how it generates jobs…"
- Emphasize: one contract, recurring jobs forever, no re-entry
- Point to the "Monthly cleaning plan" badge — frequency is visible at a glance

### Demo 3 — Route management

- **Open with:** "Once the route is committed, the dispatcher watches progress in real time…"
- When the stop turns Complete, explain auto-completion: "Route closes itself — no manual step"

### Demo 4 — Tenant admin (Operator / multi-tenant)

- **Open with:** "Office Hero is a multi-tenant platform — here's the operator view…"
- Show Tenant creation: "Onboard a new company in 30 seconds"
- Operator dashboard: "This is where we monitor all tenants from a single pane"
- Good for pitching to companies that manage multiple franchises or sub-brands

---

## Frequently asked questions during demos

**"Can the technician use their existing phone?"**  
Yes — mobile web view works on any modern Android or iPhone browser. The native Android
app is for companies that prefer it, but it's not required to get started.

**"Does it work if the technician loses signal?"**  
The mobile app queues status updates and syncs when connectivity returns.

**"How long does onboarding take?"**  
Typical setup: 30 minutes for the first admin login, first vehicle, first job, and first
dispatch. Customer data can be imported in bulk via the API or entered manually.

**"What if we already use ServiceTitan/PestPac?"**  
The integration adapters are built and ready — they just need your API credentials to
activate. No data migration required; Office Hero syncs bidirectionally.

**"What does it cost?"**  
Pricing TBD at commercial launch. Trial accounts are free.
