# Office Hero â€” Demo Video Guide

**Audience:** Sales team, account managers
**Updated:** 2026-06-27

---

## What the demos show

Four Playwright recordings walk through real end-to-end workflows against a live backend.
Each demo seeds its own isolated tenant â€” no shared state between runs.

| Demo | Duration (approx.) | What it covers |
|------|-------------------|----------------|
| **Demo 1 â€” Jobs & Dispatch** | ~3 min | Jobs list â†’ filter by status â†’ Routes page â†’ Vehicles page â†’ Dispatch form (emergency job) |
| **Demo 2 â€” Contracts lifecycle** | ~2 min | Customers page â†’ Contracts page â†’ Generated jobs from contract |
| **Demo 3 â€” Route management** | ~2 min | Route list â†’ start route via API â†’ stop progression (arrived â†’ complete) |
| **Demo 4 â€” Tenant admin** | ~2 min | Tenants page â†’ create new tenant â†’ Operator Dashboard |

---

## Option A â€” Download from CI (easiest)

Every push to `main` triggers the `demo-videos` GitHub Actions workflow (nightly at 02:00 UTC).
Videos are uploaded as artifacts named `demo-videos-<SHA>`.

1. Go to **github.com/jakez-gh/benj-office-hero/actions/workflows/demo-videos.yml**
2. Click the latest successful run
3. Under **Artifacts**, download **demo-videos-&lt;SHA&gt;**
4. Unzip â€” you'll find `.webm` files, one per demo

> **Tip:** `.webm` plays natively in Chrome and Firefox. To convert to `.mp4` for wider
> compatibility: `ffmpeg -i input.webm -c:v libx264 -c:a aac output.mp4`

---

## Option B â€” Record locally

Use this when you want fresh recordings against the latest code or a specific dataset.

### Prerequisites

```powershell
# 1. Start the backend with test auth enabled
$env:OFFICE_HERO_TEST_AUTH = "1"
poetry run uvicorn office_hero.main:app --host 127.0.0.1 --port 8000
```

```powershell
# 2. In a second terminal â€” record the demos (from repo root)
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
# From repo root â€” requires Playwright Chromium installed in apps/admin-web
node scripts/generate-sales-pdf.mjs
# Output: docs/sales/office-hero-sales-deck.pdf
```

Open `docs/sales/sales-deck.html` directly in Chrome for a live preview.

---

## Sales talking points per demo

### Demo 1 â€” Jobs & Dispatch

- **Open with:** "Here's the dispatcher's view on a typical morningâ€¦"
- Point out the status filter (pending/scheduled) â€” shows only what needs action
- Highlight the dispatch form's search field â€” type "Emergency" and watch the list narrow
- Note the vehicle auto-populates based on available crews

### Demo 2 â€” Contracts lifecycle

- **Open with:** "Riverside Cleaning Co has a monthly contract â€” here's how it generates jobsâ€¦"
- Emphasize: one contract, recurring jobs forever, no re-entry
- Point to the "Monthly cleaning plan" badge â€” frequency is visible at a glance

### Demo 3 â€” Route management

- **Open with:** "Once the route is committed, the dispatcher watches progress in real timeâ€¦"
- When the stop turns Complete, explain auto-completion: "Route closes itself â€” no manual step"

### Demo 4 â€” Tenant admin (Operator / multi-tenant)

- **Open with:** "Office Hero is a multi-tenant platform â€” here's the operator viewâ€¦"
- Show Tenant creation: "Onboard a new company in 30 seconds"
- Operator dashboard: "This is where we monitor all tenants from a single pane"
- Good for pitching to companies that manage multiple franchises or sub-brands

---

## Frequently asked questions during demos

**"Can the technician use their existing phone?"**
Yes â€” mobile web view works on any modern Android or iPhone browser. The native Android
app is for companies that prefer it, but it's not required to get started.

**"Does it work if the technician loses signal?"**
The mobile app queues status updates and syncs when connectivity returns.

**"How long does onboarding take?"**
Typical setup: 30 minutes for the first admin login, first vehicle, first job, and first
dispatch. Customer data can be imported in bulk via the API or entered manually.

**"What if we already use ServiceTitan/PestPac?"**
The integration adapters are built and ready â€” they just need your API credentials to
activate. No data migration required; Office Hero syncs bidirectionally.

**"What does it cost?"**
Pricing TBD at commercial launch. Trial accounts are free.
