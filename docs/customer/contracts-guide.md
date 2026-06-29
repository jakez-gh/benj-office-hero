<!-- Office Hero — Contracts Guide -->

# Contracts Guide

This guide explains how recurring service agreements (contracts) work in Office Hero — how to create them, how jobs auto-generate from them, and how to connect them to your back-office system. Company Admins and Dispatchers will use this guide most often; Sales staff will find the creation and linking sections relevant.

---

## What Is a Contract?

A contract in Office Hero is a recurring service agreement between your company and a customer. Once created, the contract automatically generates scheduled jobs on your chosen frequency — weekly, monthly, quarterly, or any custom interval you define — so your team never has to manually create repeat visits.

Contracts are the right tool when:

- A customer expects regular service visits (lawn care, HVAC maintenance, pest control, etc.)
- You bill on a recurring schedule tied to completed visits
- You want customer notifications to go out automatically before each visit
- You are syncing job data with an external business system

For one-off appointments, use a standard **Job** instead. See the comparison table at the end of this guide.

---

## Frequency Options

When creating a contract, you choose how often jobs are generated. The available frequencies are:

| Frequency | Jobs generated |
|---|---|
| Weekly | One job every 7 days from the start date |
| Biweekly | One job every 14 days from the start date |
| Monthly | One job on the same calendar date each month |
| Quarterly | One job every 3 months on the same calendar date |
| Custom interval | One job every N days, where you set N (minimum 1, maximum 365) |

**Monthly and quarterly notes:** If the scheduled date falls on a month that does not have that calendar day (for example, the 31st in a 30-day month), the job is generated on the last day of that month instead.

---

## Creating a Contract

Before creating a contract, confirm that the customer and their service location already exist in Office Hero. If not, add them first under **Customers**.

### Steps to create a contract

1. Navigate to **Contracts** in the left sidebar and click **New Contract**.
2. Fill in the **Customer** field — type the customer's name and select from the dropdown. Only existing customers appear here.
3. Fill in the **Location** field — select the service address for this contract. A customer may have multiple locations; choose the correct one.
4. Select the **Service Type** from the dropdown. This determines which crew capabilities are required when dispatching auto-generated jobs.
5. Choose the **Frequency** (weekly, biweekly, monthly, quarterly, or custom interval). If you choose custom, enter the number of days between visits in the **Interval (days)** field that appears.
6. Set the **Start Date** — the date the first job will be generated. The contract becomes active on this date.
7. Set the **End Date** — the last date on which a job can be generated. The contract automatically deactivates after this date. Leave this blank only if the agreement has no expiry.
8. Optionally set an **Assigned Vehicle/Crew Preference**. This is a soft preference — dispatch will suggest this vehicle or crew when auto-generated jobs are dispatched, but you can override it at dispatch time.
9. Optionally add **Notes** visible to dispatchers and technicians on each generated job.
10. Click **Save Contract**. The contract is now active and will generate its first job on the start date.

![Contract creation form](../screenshots/admin-web/desktop/07-contracts.png)

---

## How Jobs Auto-Generate

Each morning, Office Hero checks all active contracts and creates jobs for any visits due that day. The check runs at 6:00 am in your account's configured time zone.

The auto-generated job inherits the following from the contract:

- Customer and location
- Service type
- Any assigned vehicle/crew preference
- Dispatcher and technician-facing notes

The generated job appears in the **Jobs** list with a status of **Unscheduled** and a contract badge showing which contract it came from. It is not dispatched automatically — a Dispatcher or Company Admin must review and dispatch it, just like any other job.

**Notification timing:** If your account has customer notifications enabled, the customer receives an email or SMS reminder 24 hours before the scheduled visit date, not at job generation time.

---

## Manually Triggering "Generate Due Jobs"

If you need jobs to appear immediately — for example, after creating a contract with today as the start date — you can trigger generation manually without waiting for the 6:00 am automatic run.

### Steps to generate due jobs manually

1. Navigate to **Contracts** in the left sidebar.
2. Click the contract you want to generate jobs from.
3. On the contract detail page, click the **Generate Due Jobs** button in the top-right corner.
4. A confirmation dialog shows you how many jobs will be created and for which dates.
5. Click **Confirm**. The jobs appear in the **Jobs** list within a few seconds.

**Note:** The system only generates jobs that are due on or before today. You cannot pre-generate future jobs using this button — those are created automatically on their scheduled date.

---

## Pausing and Resuming a Contract

Pausing a contract stops all future job generation while keeping the contract record intact. Paused contracts do not generate jobs on their scheduled dates. Any jobs that were already generated before the pause are unaffected and remain in the **Jobs** list.

### Steps to pause a contract

1. Navigate to **Contracts** and click the contract you want to pause.
2. Click the **Pause Contract** button on the contract detail page.
3. Confirm the action in the dialog. The contract status changes to **Paused** immediately.

No jobs are generated while the contract is paused, even if scheduled visit dates pass during the pause period. Missed visits are not retroactively generated when you resume.

### Steps to resume a contract

1. Navigate to **Contracts** and click the paused contract.
2. Click **Resume Contract**.
3. Select a **Resume Date** in the dialog — this becomes the anchor date for the next job. If you select today, the next job generates at 6:00 am tomorrow (or immediately if you click **Generate Due Jobs** manually).
4. Click **Confirm Resume**. The contract status returns to **Active** and job generation continues on the next scheduled date.

---

## Linking a Contract to a Back-Office System

Office Hero can connect to external field service and business management platforms — including ServiceTitan, PestPac, and Jobber — so that contract and job data stays in sync without manual re-entry.

When a contract is linked to an external system, it can:

- **Pull** customer, location, and service agreement data from your external system into Office Hero
- **Push** completed job records, technician notes, and status updates back to your external system

### Steps to link a contract to an external system

1. Confirm that your back-office integration is connected at the account level. Go to **Settings → Integrations** and verify your external system shows a green **Connected** status. If not, follow the integration setup instructions for your platform, or contact support.
2. Open the contract you want to link.
3. Click **Link to External System** on the contract detail page.
4. Select your connected platform from the dropdown.
5. Enter the **External Record ID** — this is the ID or agreement number from your external system that corresponds to this contract. Your external system's documentation or support team can help you find this ID.
6. Choose the sync direction:
   - **Two-way sync** — changes in either system update the other
   - **Pull only** — your external system is the source of truth; Office Hero reads from it
   - **Push only** — Office Hero is the source of truth; completed job data is sent to the external system
7. Click **Save Link**. The contract detail page now shows a linked badge with the external system name.

**Important:** Changing a linked contract's core fields (customer, location, frequency) in Office Hero will push those changes to the external system if two-way sync is enabled. Verify your external system's business rules before making bulk changes to linked contracts.

![Contract linked to an external back-office system](../screenshots/admin-web/desktop/08-routes.png)

---

## Contracts vs. One-Off Jobs — Comparison

Use this table to decide whether to create a contract or a standard job.

| | Contract | One-Off Job |
|---|---|---|
| **Scheduling** | Jobs generated automatically on a recurring schedule | Single job created manually for a specific date |
| **Billing trigger** | Triggered per completed visit, tied to contract billing cycle | Triggered on completion of that single job |
| **Recurrence** | Built in — weekly, biweekly, monthly, quarterly, or custom | None — each job is independent |
| **Customer notification** | Automatic reminder sent before each generated visit | Manual or triggered on dispatch, depending on account settings |
| **Cancellation** | Pause or end-date the contract; existing jobs remain | Cancel the individual job directly |
| **Integration sync** | Full two-way, pull-only, or push-only sync with external system | Push-only on job completion (if integration is connected) |
| **Assigned crew preference** | Set once on contract; inherited by every generated job | Set per job at dispatch time |
| **Best for** | Ongoing service agreements, maintenance plans, pest control rounds | One-time repairs, emergency calls, project-based work |

---

## Getting Help

| Channel | Details |
|---|---|
| Email | <support@officehero.dev> |
| In-app chat | Click the **?** icon in the bottom-right corner of any screen |
| Phone | 1-800-HERO-FSM (available Mon–Fri, 7 am–8 pm local time) |

For integration setup or account-level configuration, Company Admins can also reach us through **Account → Support** inside the app.
