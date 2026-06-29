<!-- title: Admin Guide -->

# Office Hero Admin Guide

This guide is the complete reference for Company Admins and Dispatchers managing daily operations in Office Hero. Whether you run a plumbing crew of three or a multi-vehicle HVAC fleet, every feature you need is covered here — user management, vehicle and crew setup, customer records, job lifecycle, route operations, and handling the unexpected.

For help beyond this guide, reach us at **<support@officehero.dev>**, via the in-app chat bubble, or by phone at **1-800-HERO-FSM**.

---

## Managing Users

Your account controls who can log in, what they can see, and what they can do. Users are scoped entirely to your company — your data is isolated from all other accounts on the platform.

### Invite a New User

1. Open **Settings → Users** from the left navigation.
2. Click **Invite User**.
3. Enter the new user's name and work email address.
4. Select a role from the dropdown (see the Role Descriptions table below).
5. Click **Send Invitation**. The user receives an email with a secure link valid for 48 hours.
6. Once the user accepts and sets a password, their status changes from *Pending* to *Active*.

### Assign or Change a Role

1. In **Settings → Users**, find the user in the list.
2. Click the user's name to open their profile.
3. Select a new role from the **Role** dropdown.
4. Click **Save Changes**. The new permissions apply immediately on the user's next page load.

### Deactivate a User

1. Open the user's profile via **Settings → Users**.
2. Click **Deactivate Account**.
3. Confirm the action in the dialog. The user is logged out of all active sessions immediately and cannot log back in. Their historical records (jobs completed, notes left) are preserved.

### Role Descriptions

| Role | What They Can Do |
|---|---|
| **Company Admin** | Full access: user management, billing, all settings, all jobs and routes, all reports. |
| **Dispatcher** | Create and dispatch jobs, manage routes and vehicles, view all customers. Cannot access billing or invite users. |
| **Sales** | Create and edit customers, contracts, and jobs. Cannot dispatch or modify routes. |
| **Technician** | View their own assigned route and jobs, update job status and add notes from the field. |
| **Technician Helper** | View-only access to the job currently in progress for their crew. Cannot update status or add records. |

---

## Managing Vehicles

Vehicles represent the physical units your crews drive to jobs each day.

### Add a Vehicle

1. Go to **Vehicles** in the left navigation.
2. Click **Add Vehicle**.
3. Enter a name (e.g., "Truck 1 — HVAC East"), the licence plate, and an optional notes field.
4. Click **Save**. The vehicle is now available for crew assignment.

![Vehicles list](../screenshots/admin-web/desktop/04-vehicles.png)

### Edit Vehicle Details

1. In **Vehicles**, click the vehicle name to open its detail page.
2. Edit any fields — name, plate, or notes.
3. Click **Save Changes**.

### Assign a Crew for the Day

Crew assignments are per-day so your lineup can change without affecting historical records.

1. In **Vehicles**, click the vehicle name.
2. Under **Today's Crew**, click **Assign Technician**.
3. Search for the technician by name and select them. Repeat to add more crew members (e.g., a helper).
4. Click **Save**. The vehicle now appears on the Dispatch board with its crew for the day.

### Remove a Crew Assignment

1. Open the vehicle detail page.
2. Under **Today's Crew**, click the **×** next to the technician's name.
3. Confirm the removal. The technician is unassigned for the day; any active route on that vehicle is not affected automatically — see Day-of Exceptions if you need to reassign a route.

---

## Managing Customers and Locations

A customer record holds contact information and can carry multiple service addresses. This is common when a business customer has several locations, or when a homeowner owns rental properties.

### Add a Customer

1. Go to **Customers** in the left navigation and click **Add Customer**.
2. Fill in the customer's name, primary phone number, and email address.
3. Add the first service address under **Locations** — enter the full street address.
4. Click **Save Customer**.

![Customers list](../screenshots/admin-web/desktop/06-customers.png)

### Add Additional Service Addresses

1. Open the customer record by clicking their name.
2. Under the **Locations** section, click **Add Location**.
3. Enter the address details and an optional location nickname (e.g., "Warehouse" or "Back Office").
4. Click **Save Location**. The new address immediately becomes available when creating jobs for that customer.

### Edit or Deactivate a Customer

1. Open the customer record.
2. To edit details, update any field and click **Save Changes**.
3. To deactivate, click **Deactivate Customer** at the bottom of the page. Deactivated customers do not appear in search results or job creation forms. All their past records are retained and visible in reports.

---

## Managing Jobs

Jobs are the core unit of work in Office Hero — a single visit to a customer location to perform a service.

### Create a Job

1. Go to **Jobs** and click **New Job**.
2. Search for and select the customer.
3. Select the service address for this visit.
4. Choose the service type, set an estimated duration, and optionally add internal notes.
5. Set a requested date and time window (e.g., "morning" or "2 pm – 4 pm").
6. Click **Create Job**. The job enters **Pending** status and waits for dispatch.

![Jobs board](../screenshots/admin-web/desktop/02-jobs.png)

### Edit a Job

1. Click the job in the **Jobs** list to open its detail page.
2. Edit any field — customer, address, date, duration, or notes.
3. Click **Save Changes**. If the job has already been dispatched, editing date or duration flags the route for review.

### Filter Jobs

Use the filter bar at the top of the **Jobs** list to narrow the view:

- **Status** — filter to Pending, Dispatched, In Progress, Complete, or Cancelled.
- **Date** — pick a single date or a date range.
- **Technician** — filter to jobs assigned to a specific crew member.
- **Customer** — type a customer name to show only their jobs.

Filters stack. Clear them individually or click **Reset Filters** to return to the full list.

### Bulk Actions

1. In the **Jobs** list, check the boxes beside each job you want to act on.
2. The **Bulk Actions** toolbar appears at the top of the list.
3. Select **Reassign** to move the selected jobs to a different vehicle or technician, or **Cancel** to cancel all selected jobs at once.
4. Confirm the action in the dialog. A summary of affected jobs is shown before you commit.

---

## Understanding Job Status

Every job moves through a defined lifecycle. The table below describes each status, what triggers the transition, and who is responsible.

| Status | Meaning | Triggered By |
|---|---|---|
| **Pending** | Job has been created but not yet assigned to a vehicle or technician. | System — on job creation. |
| **Dispatched** | Job has been assigned to a vehicle and added to a route. The crew knows about it. | Dispatcher — via the Dispatch screen or auto-dispatch. |
| **In Progress** | The technician has marked themselves as arrived at the location and work has begun. | Technician — via the mobile app or tech web view. |
| **Complete** | Work is finished. The technician has checked out and any required notes or photos have been submitted. | Technician — via the mobile app or tech web view. |
| **Cancelled** | The job was called off before or during service. Stop data is preserved for billing audit. | Dispatcher or Company Admin — via the Jobs list or day-of exception flow. |

**Key rule:** a job cannot jump statuses. It must pass through Dispatched before it can go In Progress, and through In Progress before it can be marked Complete. If a technician arrives and the job is still Pending, a Dispatcher must dispatch it first.

---

## Managing Routes

A route is the ordered sequence of job stops assigned to a vehicle for a specific day. Routes are the operational plan your field crews follow.

### View the Day's Routes

1. Go to **Dispatch** in the left navigation.
2. The board shows each vehicle as a column with its stops listed in sequence.
3. Click any stop card to open the underlying job.

![Dispatch board](../screenshots/admin-web/desktop/03-dispatch.png)

### Dispatch Jobs — Choosing a Strategy

When you click **Dispatch** on one or more pending jobs, Office Hero offers three automatic sequencing options:

| Strategy | How It Works | Best For |
|---|---|---|
| **Nearest** | Assigns the job to the closest available vehicle at that time of day, minimising drive distance. | Emergency calls and tight geographies. |
| **Earliest** | Assigns to whichever vehicle has the earliest opening that fits the job's duration. | Meeting a specific customer time window. |
| **Balanced** | Distributes work across vehicles to equalise total job load and drive time. | Routine daily scheduling. |

After choosing a strategy, you can switch to **Custom Sequence** to drag stops into the exact order you prefer before confirming.

### Start a Route

1. On the **Dispatch** board, click the vehicle column's **Start Route** button.
2. Confirm the crew is ready. The route status changes to **Active** and the first stop is pushed to the technician's device.

### Cancel a Route

1. On the **Dispatch** board, open the vehicle column menu (three-dot icon).
2. Select **Cancel Route**.
3. Confirm the action. All *Dispatched* stops on the route revert to *Pending* so they can be reassigned.

### Resequence Stops

1. On the **Dispatch** board, click **Edit Sequence** on the vehicle column.
2. Drag stop cards to the desired order.
3. Click **Save Sequence**. The updated order is pushed to the technician's device immediately, even if the route is already active.

---

## Day-of Exceptions

Real days rarely match the plan. Office Hero gives you fast paths for the three most common disruptions.

### Technician Calls In Sick — Reassign a Route

1. Go to **Dispatch** and find the affected vehicle's column.
2. Open the column menu and select **Reassign Route**.
3. Choose a target vehicle from the dropdown. Only vehicles with available capacity for the day are shown.
4. Click **Confirm Reassignment**. All remaining (not yet *Complete*) stops are moved to the target vehicle and the sequence is preserved.

### Customer Cancels — Skip a Stop

1. On the **Dispatch** board, click the stop card for the job the customer cancelled.
2. Click **Skip Stop**.
3. Select a reason (Customer request, Access issue, or Other) and optionally add a note.
4. Click **Confirm Skip**. The job moves to *Cancelled* status, the route sequence closes the gap, and the technician's device updates automatically.

### Emergency Job — Insert a Stop Mid-Route

1. Create the new job via **Jobs → New Job** as normal, setting today's date.
2. On the **Dispatch** board, click **Dispatch** on the new job.
3. In the dispatch dialog, select **Insert into Active Route** and choose the target vehicle.
4. Drag the new stop to the position in the sequence where it should be inserted.
5. Click **Confirm**. The technician's device updates immediately with the new stop in sequence.

---

## Contracts and Recurring Service

Contracts let you set up recurring service agreements that generate jobs automatically, so nothing falls through the cracks for maintenance customers.

1. Open a customer record and click **New Contract**.
2. Choose the service type, the default service address, and the recurrence schedule (weekly, bi-weekly, monthly, or custom interval).
3. Set a start date and an optional end date or a fixed number of occurrences.
4. Click **Save Contract**. Jobs are created automatically on each scheduled date and appear in the **Jobs** list as *Pending*, ready for dispatch.

![Contracts](../screenshots/admin-web/desktop/07-contracts.png)

To pause a contract, open it and click **Pause**. Jobs stop generating until you click **Resume**. To end a contract early, click **Terminate Contract** — existing generated jobs are not affected.

---

## Security and Your Data

Every session in Office Hero uses encrypted connections and secure tokens. Your company's data is isolated from all other accounts on the platform — no user from another company can ever access your records, and our support team operates on a minimum-access basis. If you suspect unauthorised access, contact **<support@officehero.dev>** immediately or call **1-800-HERO-FSM**, and we will lock your account within minutes.

---

*For questions not covered here, contact us at <support@officehero.dev>, use the in-app chat, or call 1-800-HERO-FSM.*
