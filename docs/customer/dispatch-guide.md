<!-- Office Hero — Dispatch Guide -->

# Dispatch Guide

This guide covers the full dispatch workflow in Office Hero — from clicking the Dispatch button to handling emergencies, reassignments, and troubleshooting common issues. Dispatchers and Company Admins will use this guide most; Technicians may find the route and custom sequence sections useful too.

---

## How Dispatch Works

When you click **Dispatch** on a job, Office Hero calculates the best route options for your active vehicles. The system analyzes current GPS positions (refreshed every 30 seconds), each vehicle's existing stop queue, traffic conditions, and job location — all in under 8 seconds.

You do not need to wait for vehicles to check in or manually refresh the map. The system uses the most recent location data available at the moment you click Dispatch.

### What happens step by step

1. Open the job you want to dispatch from the **Jobs** list or the **Dispatch Board**.
2. Click the **Dispatch** button in the top-right corner of the job detail panel.
3. A loading indicator appears briefly — the system is calculating route options.
4. Within 8 seconds, the **Route Options** panel opens with up to three recommended options.
5. Review the options (described below), select one, and click **Confirm Dispatch**.
6. The assigned technician receives an in-app notification and the job appears on their route list.

![Dispatch board with route options panel open](../screenshots/admin-web/desktop/03-dispatch.png)

---

## The Three Auto-Generated Route Options

Office Hero always presents up to three options when you dispatch a job. Understanding what each option optimises helps you make faster, better decisions throughout the day.

| Option | What it optimises | Best used when |
|---|---|---|
| **Nearest** | Geographic distance from the vehicle to the job site | The job is urgent and response time is the top priority |
| **Earliest** | The vehicle with the soonest open time slot | The job has a deadline or customer appointment window |
| **Balanced** | Equalises stop counts across all active vehicles | Normal scheduling day; no single driver is overloaded |

### Nearest

The Nearest option assigns the vehicle whose GPS position is currently closest to the job site. This minimises drive time and is the right choice when a customer has an emergency or your dispatcher has committed to same-day service in under an hour.

**Note:** Nearest does not account for how many stops a vehicle already has queued. A nearby vehicle with a full route will still appear as Nearest if no closer vehicle exists.

### Earliest

The Earliest option assigns the vehicle that has the earliest gap in its schedule large enough to fit the job — factoring in the estimated job duration you set when creating the job. If a customer books a morning appointment slot or you have a promised arrival window, choose Earliest to honour that commitment without manually checking every technician's calendar.

### Balanced

The Balanced option distributes new work so that all active vehicles end the day with a similar workload. The system measures load by total estimated job minutes remaining, not by stop count. On a normal scheduling day, defaulting to Balanced keeps your team from burning out one crew while others finish early.

### When none of the three options are ideal

If none of the three suggested options fit your situation, use **Custom Sequence** (see below) to place the job manually on any vehicle's route.

---

## Custom Sequence

Custom Sequence lets you drag and drop stops on a vehicle's route to create a manual ordering. Use this when you know something the system does not — a technician is already at a nearby site, a customer requested a specific time, or you want to batch stops by neighbourhood.

### How to create a custom sequence

1. From the **Dispatch Board**, click the vehicle whose route you want to edit. The route panel opens on the right, showing all queued stops in order.
2. Click **Edit Sequence** at the top of the route panel.
3. Drag any stop card up or down to reposition it. The estimated arrival time for each stop updates automatically as you reorder.
4. To add the new job to this vehicle's route, drag it from the **Unassigned Jobs** tray (bottom of the screen) into the desired position in the route list.
5. When the sequence looks correct, click **Save Sequence**.
6. The technician's app updates immediately with the new stop order.

**Tip:** You can reorder stops on a route that is already in progress. Stops the technician has already completed are locked and cannot be moved.

---

## Emergency Dispatch

Emergency Dispatch inserts a new job at the very top of an active vehicle's route — ahead of all other queued stops. The technician is notified immediately with an alert, not just a standard notification.

Use Emergency Dispatch when a critical call comes in and response time overrides all other scheduling considerations.

### How to trigger an emergency dispatch

1. Open the job you need to insert urgently.
2. Click the dropdown arrow next to the **Dispatch** button and select **Emergency Dispatch**.
3. The vehicle selection screen opens. Active vehicles are listed with their current GPS position and the number of stops currently ahead of them in the queue.
4. Select the vehicle you want to insert the job onto.
5. Review the impact summary, which shows the updated estimated arrival time for the emergency job and the new estimated arrival times for the stops being pushed back.
6. Click **Confirm Emergency Dispatch**.
7. The technician's app displays a high-priority alert with the new job at the top of their list. Any stop they were currently navigating to is paused and displayed below the emergency job.

**Important:** The technician must acknowledge the emergency notification before their navigation updates. If the technician does not acknowledge within 2 minutes, the dispatcher receives an alert on the Dispatch Board.

---

## Route Reassign

Route Reassign moves all remaining stops from one vehicle to another in a single action. Use this when a technician calls in sick mid-shift or a vehicle breaks down and you need to redistribute their unfinished work quickly.

### How to reassign a route

1. From the **Dispatch Board**, click the vehicle whose stops you want to redistribute.
2. Click the **Route Reassign** button at the top of the route panel.
3. The reassign screen opens. Stops the technician has already completed are not included — only pending and in-progress stops are shown.
4. Select the destination vehicle (or vehicles) from the list. You can split stops across multiple vehicles by selecting more than one destination.
   - If you select a single destination, all stops move to that vehicle.
   - If you select multiple destinations, use the checkboxes next to each stop to assign them individually.
5. Review the updated route load for each destination vehicle, shown as estimated total minutes remaining.
6. Click **Confirm Reassign**.
7. Each affected technician receives a notification listing the stops added to their route. The original technician's route is cleared.

**Note:** If any stop being reassigned has a specific customer appointment window, a warning badge appears on that stop in the reassign screen. Verify that the destination vehicle can honour the window before confirming.

---

## Troubleshooting

### "Can't dispatch — no vehicle available"

This message appears when the system cannot find any active vehicle to assign to the job.

**Common causes and fixes:**

| Cause | Fix |
|---|---|
| All vehicles are clocked out or marked offline | Ask a technician to clock in, or manually set a vehicle to Active from the **Vehicles** settings page |
| The job's required service type does not match any vehicle's assigned capabilities | Edit the vehicle's capability list in **Settings → Vehicles** to include the required service type, or change the service type on the job |
| The job location is outside all vehicles' operating zones | Expand a vehicle's zone coverage in **Settings → Vehicles → Service Zones**, or assign the job to a specific vehicle manually using Custom Sequence |
| No vehicle has a time slot available within the day's operating window | Use the **Schedule for another day** option on the job, or extend the operating window in **Settings → Dispatch Rules** |

If the problem persists after checking the above, contact support — see the end of this guide.

### "Job already scheduled"

This message means the job has already been assigned to a vehicle's route. You cannot dispatch it again while it is active.

**To resolve:**

1. Open the job and check the **Assigned To** field to see which vehicle holds it.
2. If the assignment is incorrect, click **Unassign** on the job detail page to remove it from the current route.
3. Dispatch the job again from scratch.

If the job shows as scheduled but does not appear on the technician's app, the technician may need to refresh their route list. Ask them to pull down on the route screen to force a sync.

### "Dispatch took longer than expected"

The normal calculation time is under 8 seconds. If the Route Options panel has not appeared after 20 seconds, the system may be experiencing a temporary slowdown.

**Steps to resolve:**

1. Wait 30 seconds, then click away from the job and return to it. Click **Dispatch** again.
2. If the delay persists, check the **System Status** banner at the top of the Dispatch Board. A yellow or red indicator means a known issue is being investigated.
3. As a short-term workaround, use **Custom Sequence** to manually assign the job to a vehicle without waiting for the route engine.
4. If the system status is green and delays continue for more than a few minutes, contact support.

---

## Getting Help

| Channel | Details |
|---|---|
| Email | support@officehero.dev |
| In-app chat | Click the **?** icon in the bottom-right corner of any screen |
| Phone | 1-800-HERO-FSM (available Mon–Fri, 7 am–8 pm local time) |

For billing questions or account-level changes, Company Admins can also reach us through the **Account → Support** page inside the app.
