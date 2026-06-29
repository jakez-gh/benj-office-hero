<!-- Office Hero Security Guide — for Company Admins -->

# Office Hero Security Guide

This guide explains how Office Hero protects your business data and your team's access. It is written for Company Admins who want a clear, non-technical picture of the security measures in place.

If you have a security concern at any time, email **<security@officehero.dev>**. We respond within 24 hours.

---

## Your Data Is Yours Alone

Every company that uses Office Hero has a completely separate data space. Your jobs, customers, contracts, technicians, routes, and audit records are stored in a way that makes it structurally impossible for another company's account — or their users — to see, search, or retrieve anything that belongs to you.

This is not simply a matter of filtering a shared list. The separation is enforced at the storage layer itself. Even if a software defect caused a query to run incorrectly, the rules that isolate your data would still prevent it from returning results belonging to another company. Think of it like separate locked rooms rather than separate cabinets in a shared room.

Office Hero staff can access raw infrastructure for maintenance and incident response, but all such access is logged and reviewed.

---

## How Login Works

### Secure Sessions

When you log in, Office Hero issues an encrypted session token to your browser or mobile device. This token is used to authenticate every request you make while you are signed in. It is never stored in a location that can be read by scripts or other browser extensions — it lives in a secure, HTTP-only cookie.

### Session Expiry

Sessions expire automatically after **30 minutes of inactivity**. When a session expires, you are returned to the login screen and must re-authenticate. This protects your account if you walk away from a shared device.

If you are actively using the application, your session is refreshed automatically so you are not interrupted during normal work.

### Logging Out All Devices

If you believe your account has been accessed from an unknown device, you can invalidate all active sessions at once:

1. Open **Settings** from the top navigation menu.
2. Select **Security**.
3. Click **Sign out all devices**.
4. Confirm the action.

All sessions — including any open on mobile devices or other browsers — are immediately invalidated. Anyone signed in under your credentials will be returned to the login screen.

---

## Role-Based Access

Office Hero uses roles to make sure your team members can only see and do what their job requires. Roles are assigned by a Company Admin and can be changed at any time.

### Role Descriptions

**Company Admin**
Full access to all features. Can manage users, roles, billing, integrations, audit logs, and all operational data. Typically the business owner or office manager.

**Dispatcher**
Can view, create, and dispatch jobs. Can view customers, routes, technician locations, and vehicles. Cannot manage users, view audit logs, or access billing.

**Sales**
Can manage customer records and contracts. Can view jobs but cannot dispatch them or alter routes. Cannot manage users or access financial or audit information.

**Technician**
Access is scoped to their own assigned jobs and routes. Can update job status, log notes, and capture signatures. Cannot see other technicians' schedules or any company-level settings.

**Technician Helper**
Read-only companion role for a technician's jobs. Can view job details and customer information for the jobs they are assigned to. Cannot create, edit, or close anything.

### Role Permissions at a Glance

| Action | Company Admin | Dispatcher | Sales | Technician | Technician Helper |
|---|---|---|---|---|---|
| View jobs | ✓ | ✓ | ✓ | Own only | Own only |
| Create jobs | ✓ | ✓ | ✓ | — | — |
| Dispatch jobs | ✓ | ✓ | — | — | — |
| View routes | ✓ | ✓ | — | Own only | Own only |
| Manage users | ✓ | — | — | — | — |
| View audit log | ✓ | — | — | — | — |
| Manage vehicles | ✓ | ✓ | — | — | — |
| Manage customers | ✓ | ✓ | ✓ | — | — |
| Manage contracts | ✓ | — | ✓ | — | — |
| View-only mode | ✓ | ✓ | ✓ | — | — |

---

## Audit Log

### What Is Recorded

The audit log is a chronological record of significant actions taken within your account. Every entry includes:

- **Who** performed the action (name and email)
- **What** they did (for example: created a job, updated a customer, changed a user's role, logged out all devices)
- **When** it happened (date and time, recorded in UTC)
- **Where relevant**, the record that was affected (for example: the job ID or customer name)

The audit log cannot be edited or deleted by anyone, including Company Admins or Office Hero staff.

### Who Can See It

Only users with the **Company Admin** role can access the audit log. Dispatchers, Sales users, Technicians, and Technician Helpers do not have access.

### How to Access It

1. Sign in as a Company Admin.
2. Open **Settings** from the top navigation.
3. Select **Audit Log**.
4. Use the date range filter and search box to find specific events.
5. Export to CSV if you need to share records with an auditor or legal team.

### Retention Period

Audit records are kept for **90 days**. Records older than 90 days are permanently deleted. If your business requires longer retention for compliance reasons, contact us at <support@officehero.dev> to discuss options.

---

## Encryption in Transit

All communication between your browser or mobile app and Office Hero's servers is encrypted using HTTPS (TLS 1.2 or higher). This means:

- No one on the same network can intercept your data
- Login credentials are never sent in plain text
- API requests from the mobile app are encrypted the same way as browser traffic

There is no unencrypted fallback. Connections that cannot negotiate a secure channel are rejected.

---

## Password Requirements

Office Hero enforces the following minimum requirements for all passwords:

- At least **12 characters** long
- At least **one uppercase letter**, **one lowercase letter**, **one number**, and **one special character** (for example: !, @, #, $)
- Cannot be the same as your previous three passwords
- Cannot contain your email address or username

### Recommended Practices

- Use a password manager (such as 1Password, Bitwarden, or your browser's built-in manager) to generate and store passwords.
- Never share your password with a colleague. If someone needs access, create them their own account with the appropriate role.
- If you suspect your password has been compromised, change it immediately under **Settings → Security → Change Password**, then use **Sign out all devices** to close any unauthorized sessions.

---

## Reporting a Security Concern

If you discover or suspect a security vulnerability, a data exposure, or any suspicious activity in your account, contact us immediately:

- **Email:** <security@officehero.dev>
- **Response SLA:** We acknowledge every report within **24 hours** and provide a status update within 72 hours.

Please include as much detail as you can: what you observed, when, and any screenshots or logs that may help us investigate. We treat all security reports as high priority.

For general account help that is not a security emergency:

- **Email:** <support@officehero.dev>
- **In-app chat:** available from any screen via the chat icon
- **Phone:** 1-800-HERO-FSM
- **Hours:** Monday–Friday, 8am–6pm ET
