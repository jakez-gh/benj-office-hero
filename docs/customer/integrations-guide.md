<!-- Integrations Guide — Office Hero -->

# Integrations Guide

Office Hero connects with the field service software your company may already use — so you don't have to choose between the tools your team knows and the dispatching power Office Hero provides. This guide explains what each integration does, what data moves between systems, and how to get connected.

If your company does not use any external system, skip to the next section. Office Hero works great on its own.

**Questions or ready to connect?** Contact us at support@officehero.dev, through the in-app **Help** chat, or by calling **1-800-HERO-FSM**.

---

## What Integrations Do

When Office Hero is connected to an external field service or CRM platform, it can automatically share data in both directions — reducing double entry, keeping records consistent, and making sure your technicians always have the latest job information without anyone having to re-type it.

Depending on the integration, synced data can include:

- **Customer records** — names, addresses, contact details, service history
- **Jobs and work orders** — scheduled dates, job type, notes, status updates
- **Invoices and billing** — completed job totals passed back to your invoicing system
- **Technician assignments** — which tech is assigned to which job

Every integration is configured at the company level by a Company Admin. Your data is isolated from all other accounts — only your company's records are ever synced.

---

## Office Hero as Your System of Record

If your company does not use ServiceTitan, PestPac, Jobber, or another external platform, Office Hero is fully capable of acting as your single system of record. You can:

- Manage your full customer list inside Office Hero
- Create and schedule jobs directly in the dispatcher view
- Track job history, technician notes, materials used, and customer signatures
- Generate invoices from completed jobs and export them to your accounting software (QuickBooks, Xero, or CSV export)

In this mode, nothing leaves Office Hero unless you choose to export it. All customer and job data lives in your account — encrypted, backed up continuously, and completely isolated from other companies on the platform.

This is the recommended starting point for new customers. You can add an integration later without losing any historical data.

---

## ServiceTitan Integration

### Who Uses It

ServiceTitan is popular with mid-to-large plumbing, HVAC, electrical, and multi-trade companies that need robust invoicing, service agreements, and customer communication tools. If your company runs ServiceTitan as your primary CRM and billing platform, the Office Hero integration lets you dispatch and route in Office Hero while ServiceTitan stays the source of truth for customer records and invoicing.

### What Data Syncs

| Data Type | Direction | Frequency |
|---|---|---|
| Customer records (name, address, phone, email) | ServiceTitan → Office Hero | Every 15 minutes |
| Jobs and work orders | ServiceTitan → Office Hero | Every 15 minutes |
| Technician assignments | ServiceTitan → Office Hero | Every 15 minutes |
| Job status updates (arrived, complete) | Office Hero → ServiceTitan | Real time (within 60 seconds) |
| Completed job notes and materials | Office Hero → ServiceTitan | On job completion |
| Invoices | ServiceTitan only (no sync) | N/A |

### How to Connect

1. In Office Hero, go to **Settings → Integrations → ServiceTitan**.
2. Contact us at support@officehero.dev or 1-800-HERO-FSM to initiate the connection — our team will walk you through generating the required API credentials in your ServiceTitan account.
3. Paste your ServiceTitan Tenant ID and API key into the Office Hero connection screen.
4. Tap **Connect** and confirm.

> **Security note:** Your API credentials are stored encrypted and are never visible to Office Hero support staff after the initial setup.

### After Connection

Once connected, Office Hero runs an initial sync that pulls all active customers and open jobs from ServiceTitan. For most companies, this completes within **30–60 minutes**. You will see a progress indicator on the Integrations page.

After the initial sync, data updates on the schedule shown in the table above. No manual action is needed.

### Known Limitations

- Invoice creation and management remains in ServiceTitan. Office Hero passes job completion data back, but does not generate or send invoices.
- Service agreements and recurring maintenance schedules defined in ServiceTitan are visible in Office Hero as read-only — they cannot be edited from Office Hero.
- Custom fields defined in ServiceTitan are not synced. Standard fields only.
- Technician accounts must exist in both systems. Office Hero does not create ServiceTitan user accounts automatically.

---

## PestPac Integration

### Who Uses It

PestPac (by WorkWave) is the leading platform for pest control companies. It handles scheduling, chemical usage tracking, route density, and state-mandated service records. The Office Hero + PestPac integration is designed for pest control operators who want Office Hero's real-time dispatch and GPS routing layered on top of PestPac's compliance and record-keeping capabilities.

### What Data Syncs

| Data Type | Direction | Frequency |
|---|---|---|
| Customer accounts | PestPac → Office Hero | Hourly |
| Service orders | PestPac → Office Hero | Hourly |
| Technician schedules | PestPac → Office Hero | Hourly |
| Arrival and departure timestamps | Office Hero → PestPac | On status change |
| Job completion status | Office Hero → PestPac | On job completion |
| Chemical usage records | PestPac only (no sync) | N/A |
| Service history and compliance records | PestPac only (no sync) | N/A |

### How to Connect

1. In Office Hero, go to **Settings → Integrations → PestPac**.
2. Email us at support@officehero.dev with your company name and your PestPac account number. Our team will coordinate with WorkWave on your behalf to obtain a connection token — this process typically takes **1–2 business days**.
3. Once your token is ready, we will send it to you securely. Enter it in the PestPac integration screen in Office Hero and tap **Activate**.

### After Connection

The initial sync pulls all active service orders and customer accounts. Depending on your account size, this can take up to **2 hours**. PestPac's API applies rate limits that prevent faster initial pulls — this is a PestPac constraint, not an Office Hero limitation.

After setup, syncs run hourly. Arrival and completion events push back to PestPac within 60 seconds of the technician tapping the button in the app.

### Known Limitations

- Chemical application records, pesticide tracking, and regulatory compliance documentation are PestPac-only. Office Hero does not read or write these records.
- Route density optimization features in PestPac (territory balancing) are not reflected in Office Hero routing. Office Hero routes by travel time and order sequence set by your dispatcher.
- Customer portal features in PestPac (online booking, notifications) remain independent of Office Hero.
- The hourly sync cadence means new service orders created in PestPac can take up to 60 minutes to appear in Office Hero. For urgent same-day additions, contact your dispatcher directly.

---

## Jobber Integration

### Who Uses It

Jobber is widely used by small and growing service businesses across many trades — landscaping, window cleaning, junk removal, handyman, and more. It covers quoting, scheduling, invoicing, and customer communications in one tool. The Office Hero + Jobber integration suits companies that handle customer relationships and billing in Jobber but want Office Hero's real-time GPS dispatch and optimized routing for their field team.

### What Data Syncs

| Data Type | Direction | Frequency |
|---|---|---|
| Clients (name, address, contact info) | Jobber → Office Hero | Every 10 minutes |
| Jobs and visits | Jobber → Office Hero | Every 10 minutes |
| Assigned team members | Jobber → Office Hero | Every 10 minutes |
| Job status updates | Office Hero → Jobber | Real time (within 30 seconds) |
| Completion notes and photos | Office Hero → Jobber | On job completion |
| Quotes and invoices | Jobber only (no sync) | N/A |
| Client-facing communications | Jobber only (no sync) | N/A |

### How to Connect

1. In Office Hero, go to **Settings → Integrations → Jobber**.
2. Click **Connect with Jobber**. You will be redirected to Jobber's authorization page.
3. Sign in to your Jobber account and click **Allow Access** to grant Office Hero permission to read and update your job data.
4. You will be redirected back to Office Hero automatically. The connection is active immediately.

> This is the only integration that uses direct OAuth authorization — no API keys or support tickets required. The connection takes under 2 minutes.

### After Connection

Jobber's API allows near-real-time data access, so the initial sync is fast — most companies see all current clients and open jobs appear in Office Hero within **5–10 minutes**. New jobs added in Jobber appear in Office Hero within the 10-minute sync window.

### Known Limitations

- Quotes, estimates, and invoice management remain in Jobber. Office Hero does not create or modify financial documents.
- Client reminders, follow-up emails, and Jobber's built-in client notification features are not triggered by Office Hero status updates — Jobber triggers those from its own job records, which are updated when Office Hero pushes status back.
- Recurring job series created in Jobber sync visit by visit. Office Hero shows individual visits, not the parent recurring series.
- The Jobber connection uses your authorization credentials. If your Jobber password changes or you revoke access, you will need to reconnect from Settings → Integrations → Jobber.

---

## Integration Comparison

| Integration | Best For | Sync Direction | Setup Time | Key Limitation |
|---|---|---|---|---|
| **ServiceTitan** | Mid-to-large plumbing, HVAC, multi-trade | Both directions | 1–2 hours with support | Invoicing stays in ServiceTitan; no custom field sync |
| **PestPac** | Pest control companies with compliance requirements | Both directions | 1–2 business days | Chemical/compliance records never leave PestPac; hourly cadence |
| **Jobber** | Small service businesses (landscaping, handyman, cleaning) | Both directions | Under 2 minutes (self-serve OAuth) | Quotes and invoices stay in Jobber; recurring series not visible as series |
| **None (Office Hero only)** | New companies or those without an external platform | Internal only | Immediate | Manual import needed for existing customer lists |

---

## Getting Help

Setting up an integration is a one-time task, and we are here to help you through it. Reach us at:

- **Email:** support@officehero.dev
- **In-app chat:** tap **Help** in the bottom navigation bar
- **Phone:** 1-800-HERO-FSM

Integration support is included with all Office Hero plans. There is no extra charge for connecting your external system.
