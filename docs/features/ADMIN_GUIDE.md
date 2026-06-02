# Office Hero - Administrator Guide

**Version:** 1.0 MVP  
**Audience:** TenantAdmins, Dispatchers  
**Last Updated:** June 2, 2026

---

## Overview

Office Hero is a dispatch and route management system that helps you assign jobs to technicians efficiently. This guide covers dispatching jobs, managing routes, and tracking technician progress.

**Key Features:**
- 3-option dispatch (nearest, earliest, balanced)
- Custom route sequencing
- Real-time technician tracking
- Automatic route completion
- Full audit trail of all actions

---

## Getting Started

### 1. Login

Visit `https://admin.officehero.dev`

1. Enter your email and password
2. Click "Sign In"
3. You'll see the main dashboard

### 2. Main Dashboard

The dashboard shows:
- **Today's Overview:** Route count, vehicle status, jobs pending
- **Quick Actions:** Dispatch new job, view routes, add customer
- **Active Routes:** Routes in progress with stop count
- **Pending Jobs:** Jobs waiting to be dispatched

---

## Dispatching Jobs

### Step 1: Create a Job

1. Click **"+ New Job"** in the top right
2. Fill in:
   - **Customer:** Select existing or create new
   - **Service Type:** Plumbing, HVAC, Electrical, etc.
   - **Location:** Address (auto-geocoded)
   - **Estimated Duration:** 30, 60, 90 minutes
   - **Details:** Job-specific information
   - **Priority:** Standard, High, or Urgent
3. Click **"Create Job"**

The job is now **Pending** and ready for dispatch.

### Step 2: View Routing Options

1. Click the job in your "Pending Jobs" list
2. Click **"View Routing Options"**

You'll see 3 ranked options:

| Option | What It Means | When to Use |
|--------|---------------|-------------|
| **Nearest** | Closest vehicle to job location | Most jobs |
| **Earliest** | Minimizes total route time | Time-sensitive jobs |
| **Balanced** | Most even workload across vehicles | Fairness priority |

Each option shows:
- Assigned vehicle
- Estimated distance and time
- Current vehicle location
- Crew members assigned

### Step 3: Dispatch to a Vehicle

#### Option A: Quick Dispatch
1. Click **"Dispatch to Nearest"** (recommended for 80% of jobs)
2. Review the vehicle and crew assigned
3. Click **"Confirm"**

**Route created!** The technician will see it immediately.

#### Option B: Choose Different Option
1. Click on "Earliest" or "Balanced" tab
2. Review the alternative
3. Click **"Dispatch"**

#### Option C: Custom Sequence
1. Click **"Custom Sequence"** tab
2. Drag jobs to reorder them
3. Make sure your current job is included in the sequence
4. Click **"Dispatch with Custom Sequence"**

---

## Managing Routes

### View Routes

1. Click **"Routes"** in the sidebar
2. Select a date
3. Click on any route to see details

### Route Details

Each route shows:
- Vehicle and crew assigned
- All stops (jobs) in sequence
- Stop status (Pending, Arrived, Complete, Skipped)
- Total distance and estimated time
- Actual arrival and completion times

### Transition Route States

#### Start Route
When technician begins work:
1. Open the route
2. Click **"Start Route"**
3. Status changes to "In Progress"

#### Cancel Route
If circumstances change:
1. Open the route
2. Click **"Cancel Route"**
3. Enter reason (required)
4. All scheduled jobs return to **Pending**

**Note:** Can only cancel routes in "Committed" or "In Progress" status.

### Track Stop Progress

Watch as technician updates stops:

| Stop Status | What It Means | Next Step |
|-------------|---------------|-----------|
| **Pending** | Technician heading to job | Technician marks arrived |
| **Arrived** | Technician at customer location | Technician marks complete |
| **Complete** | Work finished, technician left | Next stop or route complete |
| **Skipped** | Job skipped, moved to pending | Re-dispatch later |

**Route Auto-Completes:** When the last stop is complete, the route automatically transitions to "Complete".

---

## Managing Vehicles & Crews

### Assign Crews

Before dispatching, ensure crews are assigned:

1. Click **"Vehicles"** in the sidebar
2. Click a vehicle
3. Click **"Assign Crew"**
4. Select technicians for today
5. Click **"Save"**

**Must have:** At least 1 crew member assigned to a vehicle before dispatching.

---

## Real-Time Tracking

### Vehicle Locations

See where technicians are in real-time:

1. Click **"Routes"**
2. Click a route in progress
3. View the **Location** section
4. Technician location updates every 30 seconds

### Route Map (Future)

Coming soon: Interactive map showing all vehicle locations and route overlays.

---

## Handling Issues

### Technician Can't Find the Address

1. Open the stop
2. Look at the recorded address and GPS coordinates
3. Call technician with correct directions or update address
4. Job continues normally

### Job Takes Longer Than Estimated

1. Open the route
2. Next stops' ETAs automatically recalculate
3. No action needed unless it affects crew assignments
4. Technician marks complete when done

### Technician Can't Complete a Stop

1. Technician marks stop **"Skipped"** with reason
2. Job returns to **Pending**
3. You can:
   - Dispatch it to a different vehicle
   - Reschedule for tomorrow
   - Mark as cancelled if customer cancelled

### Technician Unavailable Mid-Route

1. Open the route
2. Click **"Cancel Route"**
3. All stops return to Pending
4. Re-dispatch remaining jobs to other vehicles

---

## Reports & Analytics

### Today's Summary
- Routes completed
- On-time percentage
- Average service time
- Technician utilization

### Audit Trail
Every action is logged:
- Who dispatched each job
- When routes were created/started/completed
- Which technician marked each stop
- Any route cancellations with reasons

Access via: **"Settings" → "Audit Log"**

---

## Best Practices

### Dispatching
1. **Batch dispatch:** Group related jobs to same technician
2. **Check traffic:** Consider rush hours when estimating
3. **Balance workload:** Use "Balanced" option to prevent overload
4. **Confirm crews:** Always verify crew is assigned before dispatching

### Managing Routes
1. **Start early:** Begin routes 30 min before first job
2. **Monitor progress:** Check mid-route for delays
3. **Communicate:** Text/call technician if customer request changes
4. **Complete records:** Ensure all stops marked before route considered done

### Customer Communication
1. **Give time windows:** "We'll arrive between 10am-12pm"
2. **Provide GPS:** Send stop location via SMS/email
3. **Notify completion:** Confirm job done within 1 hour
4. **Collect feedback:** Ask about technician professionalism

---

## Troubleshooting

### "Can't dispatch - no vehicle available"

**Cause:** All vehicles already have committed routes for that date/time

**Solution:**
- Check if vehicle has crew assigned
- Try different routing option
- Postpone to next day

### "Route won't cancel"

**Cause:** Route is already completed

**Solution:**
- Only "Committed" and "In Progress" routes can be canceled
- If all stops complete, route auto-completes (can't cancel)

### "Technician can't see route"

**Cause:** Tech-web not loading, or crew not assigned

**Solution:**
1. Verify crew is in the route
2. Have technician reload their browser
3. Check their internet connection
4. Try tech-mobile app instead of web

### "Dispatch says 'job already scheduled'"

**Cause:** Job was previously dispatched and is still pending dispatch completion

**Solution:**
- Cancel previous dispatch first
- Or mark first dispatch as "Skipped"

---

## Support

For help:
- Email: support@officehero.dev
- Chat: In-app support (bottom right)
- Phone: 1-800-OFFICE-HERO

---

**Next:** Technician Guide  
**Admin Training:** 30 minutes  
**Typical Dispatch Time:** 2-3 minutes per job

