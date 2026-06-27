<!-- Office Hero Frequently Asked Questions -->

# Office Hero — Frequently Asked Questions

---

## Getting Started

**Q: What do I need to get started with Office Hero?**
A: You need a modern web browser (Chrome, Edge, Firefox, or Safari) and an internet connection. There is nothing to install on a desktop computer. Your Company Admin will receive a welcome email with a link to set up your account and invite your team members.

**Q: How do I invite a team member?**
A: Sign in as a Company Admin, go to **Settings → Users**, and click **Invite User**. Enter their name, email address, and select their role. They will receive an email with a secure link to set their password and sign in. The invite link expires after 48 hours — you can resend it from the Users list if needed.

**Q: Can I change a team member's role after they have been set up?**
A: Yes. Go to **Settings → Users**, click the team member's name, and select a new role from the dropdown. The change takes effect immediately — their next page load will reflect the updated permissions. You do not need to ask them to log out and back in.

**Q: How do I set up my company's vehicles?**
A: Go to **Settings → Vehicles** and click **Add Vehicle**. Enter the vehicle's name or identifier, type (van, truck, car, etc.), and license plate. You can assign a default technician to a vehicle, though vehicles can also be reassigned to a different technician when creating a dispatch. Vehicles must be set up before they can appear as dispatch options.

**Q: Is there a mobile app for my office staff?**
A: The full Office Hero web application is mobile-responsive and works well on tablets and smartphones via a browser. A dedicated mobile app optimized for field technicians is also available — see the Technician App section below. Office staff (dispatchers, admins, sales) typically use the web application from a desktop or tablet.

**Q: How do I reset my password?**
A: On the login screen, click **Forgot password?** and enter your email address. You will receive a reset link within a few minutes. The link is valid for one hour. If you do not see the email, check your spam folder or contact your Company Admin to resend an invite.

**Q: Can I use Office Hero offline?**
A: The web application requires an internet connection. The Technician mobile app caches the current day's job details so technicians can view their assigned jobs and customer information if they temporarily lose signal. Any updates made offline sync automatically when the connection is restored.

---

## Jobs & Dispatch

**Q: How long does dispatch take?**
A: Office Hero generates up to three route options — Nearest, Earliest, and Balanced — in under 8 seconds. You can also create a custom sequence by dragging stops into your preferred order. Once you confirm a dispatch option, the technician's route updates immediately.

**Q: What is the difference between Nearest, Earliest, and Balanced route options?**
A: Nearest prioritizes getting the closest available technician to the job. Earliest optimizes for the soonest arrival time, accounting for current traffic conditions. Balanced spreads workload across your available technicians to avoid overloading any single person. All three options are shown simultaneously so you can compare and choose the one that best fits the situation.

**Q: Can I manually change a technician's route after dispatch?**
A: Yes. Open the active dispatch in the **Dispatch** view, click **Edit Route**, and drag jobs into a different order or reassign a job to a different technician. The technician's app updates in real time. Any changes are logged in the audit log with your name and timestamp.

**Q: Can I dispatch multiple technicians to the same job?**
A: Yes. When creating or editing a job, you can assign both a primary Technician and one or more Technician Helpers. All assigned team members see the job in their app and share the same route stop. Job notes and status updates from any team member are visible to the whole assigned team.

**Q: What job statuses are available?**
A: Jobs move through the following statuses: **Scheduled → Dispatched → En Route → On Site → Completed** (or **Cancelled**). Technicians update the status from their app. Dispatchers and Admins can also update status from the web application. You can filter the Jobs list by status to see what is active at any moment.

**Q: Can I have the same customer at multiple addresses?**
A: Yes. Each customer record can have unlimited service locations. When creating a job, select the customer first, then choose which of their addresses the job is for. All job history is visible at both the customer level and the individual location level.

**Q: Can I attach photos or documents to a job?**
A: Yes. Technicians can attach photos directly from their mobile app — useful for before-and-after documentation, equipment photos, or proof of work. Dispatchers and Admins can attach files (PDF, image) from the web application. All attachments are stored against the job record and are visible to anyone with access to that job.

**Q: How do I capture a customer signature?**
A: When a technician completes a job, they can request a customer signature through the mobile app. The customer signs on the technician's screen, and the signed record is attached to the completed job automatically. Company Admins and Dispatchers can view the signature from the job detail page in the web application.

---

## Routes & Tracking

**Q: How often does the technician's location update?**
A: Technician GPS location refreshes every 30 seconds when the mobile app is active and a route is in progress. The Dispatch map view shows each technician's most recent position. Location tracking is only active when the technician has a dispatched route — it does not run continuously outside of working hours.

**Q: Can technicians see each other's locations?**
A: No. Each technician's app shows only their own route and job details. Only Dispatchers and Company Admins can see the full fleet map with all technician positions.

**Q: What happens if a technician's phone loses signal mid-route?**
A: The app caches the current route so the technician can continue working from their cached job list. Any status updates or notes they enter while offline are stored locally and synced to Office Hero as soon as the connection is restored. The Dispatch map will show the technician's last known position until a new location update comes through.

**Q: Can I see a technician's historical route for a past day?**
A: Yes. From the **Reports** section, select **Route History**, choose the technician and date range, and you will see a playback of their route with timestamps at each stop. This is useful for resolving customer disputes or verifying field activity.

**Q: Does Office Hero account for traffic when calculating routes?**
A: Yes. Route options are calculated using real-time traffic data. If traffic conditions change after a route is dispatched, the app will flag the affected stop with an updated ETA and notify the dispatcher. You can choose to re-route, notify the customer, or leave the original schedule in place.

**Q: Can I set a geographic service area for my company?**
A: Yes. Under **Settings → Service Area**, you can define one or more regions by drawing on a map or entering zip codes. Jobs outside your service area will display a warning at creation time. This is a soft warning — you can still accept and dispatch the job — but it helps catch address errors before a technician drives out of range.

---

## Contracts

**Q: What types of contracts does Office Hero support?**
A: Office Hero supports recurring service contracts (such as annual maintenance plans) and single-service agreements. Recurring contracts can be configured with any schedule — weekly, monthly, quarterly, or custom — and automatically generate jobs on the specified dates.

**Q: Who can create and manage contracts?**
A: Users with the Company Admin or Sales role can create, edit, and close contracts. Dispatchers can view contracts but cannot modify them. Technicians and Technician Helpers cannot access contracts.

**Q: Can I attach a contract to multiple service locations for the same customer?**
A: Yes. A contract is linked to a customer record and can cover one or more of that customer's service locations. When the contract auto-generates jobs, each location generates its own job so they can be independently dispatched and tracked.

**Q: What happens when a contract expires?**
A: Seven days before a contract's end date, the Company Admin and any Sales users assigned to the customer receive an in-app notification and an email reminder. The contract is not renewed automatically — a user must manually renew or extend it. Expired contracts are moved to **Inactive** status and no longer generate new jobs, but their history remains accessible.

**Q: Can I export contract data for reporting or billing?**
A: Yes. From the **Contracts** list, use the **Export** button to download a CSV of all contracts (or a filtered subset) with key fields: customer name, locations, service type, value, start and end dates, and status. For billing integrations, see the Integrations section.

---

## Technician App

**Q: Where do I download the technician app?**
A: The Office Hero Technician app is available for Android on the Google Play Store. Search for "Office Hero" and look for the official app published by Office Hero. An iOS version is in development — in the meantime, iOS users can access the mobile-responsive web application through Safari.

**Q: Does the technician need to create their own account?**
A: No. The Company Admin or Dispatcher creates the technician's user account and assigns them the Technician role. The technician receives a welcome email with a link to set their password. Once their password is set, they log in to the app with their email and that password.

**Q: How does the technician know when a new job is assigned?**
A: The app sends a push notification when a new job is dispatched to the technician. The technician will also see the job appear in their **My Jobs** list the next time they open the app, even if they dismissed the notification.

**Q: Can a technician add notes or comments to a job?**
A: Yes. From any job detail screen, the technician can tap **Add Note** to enter free text, attach a photo, or log materials used. Notes are time-stamped and visible to Dispatchers and Admins in the web application immediately. Notes cannot be deleted by the technician — only a Company Admin can remove a note.

**Q: What if a technician finishes all their jobs early?**
A: The technician's app will show no further scheduled stops. The dispatcher can add new jobs to their route at any time — the technician will receive a push notification and the new stop will appear in their app without needing to restart it.

---

## Account & Billing

**Q: How is Office Hero priced?**
A: Office Hero is billed monthly or annually, based on the number of active users on your account. Active users are those who have accepted their invite and can log in — deactivated accounts do not count toward your user total. Contact support@officehero.dev for current plan details and pricing.

**Q: How do I update my billing information?**
A: Go to **Settings → Billing** and click **Update Payment Method**. You can replace a credit or debit card, or switch to ACH bank transfer. Changes take effect on your next billing cycle. Only Company Admins can access billing settings.

**Q: What happens if a payment fails?**
A: You will receive an email notification immediately when a payment fails. Office Hero will retry the charge automatically over the following three days. If the charge has not succeeded after three attempts, your account is placed in a read-only grace period for seven days, during which no new jobs or dispatches can be created but all existing data remains accessible. Restoring a valid payment method immediately exits the grace period.

**Q: How do I deactivate a user who has left my company?**
A: Go to **Settings → Users**, click the user's name, and select **Deactivate Account**. Their active session is invalidated immediately — they cannot log in again. Their name and activity history remain in the audit log and on historical job records. If you need to permanently delete a user's personal data (for example, for a data subject access request), contact support@officehero.dev.

**Q: Can I export all of my company's data?**
A: Yes. Under **Settings → Data Export**, you can request a full export of your account data including customers, jobs, contracts, routes, and users in CSV format. Exports are generated asynchronously and emailed to the requesting Company Admin within one hour for most account sizes.

---

## Integrations

**Q: Does Office Hero integrate with QuickBooks?**
A: Yes. The QuickBooks Online integration syncs completed jobs and contract invoices to your QuickBooks account. To connect, go to **Settings → Integrations → QuickBooks** and follow the authorization steps. Once connected, completed jobs with a billable amount automatically create a draft invoice in QuickBooks. You review and send the invoice from within QuickBooks.

**Q: Can I connect Office Hero to my existing CRM or ERP system?**
A: Office Hero supports webhook-based integrations that can push job and customer events to external systems in real time. For deeper integrations with specific CRM or ERP platforms, contact support@officehero.dev to discuss your use case. Our team can advise on available options and any custom integration work.

**Q: Does Office Hero support calendar integration?**
A: A read-only iCal feed is available for each technician's schedule, which can be subscribed to from Google Calendar, Apple Calendar, or Outlook. Go to **Settings → Integrations → Calendar Feed** to generate the subscription link. Note that the calendar feed is read-only — jobs must still be created and managed within Office Hero.

**Q: Can customers book jobs online?**
A: A customer-facing booking portal is on the product roadmap. In the meantime, customers can contact your office and a dispatcher can create the job on their behalf. If you want to be notified when the booking portal launches, add your email on the **Feature Waitlist** page under **Settings → Integrations**.

---

## Security

**Q: Is my company's data visible to other companies using Office Hero?**
A: No. Every company's data is completely isolated. Your jobs, customers, contracts, and team information are not visible to — and cannot be accessed by — any other company on the platform. This separation is enforced at the infrastructure level, not just through software filters.

**Q: What happens to my data if I cancel my account?**
A: Your data is retained for 30 days after cancellation, giving you time to export anything you need. After 30 days, all data associated with your account is permanently deleted from our systems. If you need an extended retention period before deletion, contact support@officehero.dev before the 30-day window closes.

**Q: Does Office Hero comply with data protection regulations?**
A: Office Hero is designed with data privacy in mind. All data is encrypted in transit. User access is controlled by role-based permissions. Audit logs track all significant actions. If your business operates under specific regulatory requirements (such as CCPA or state-level privacy laws), contact support@officehero.dev to discuss your compliance needs — we are happy to provide documentation to support your compliance review.

---

## Still Have Questions?

Our support team is here to help.

| Channel | Details |
|---|---|
| Email | support@officehero.dev |
| In-app chat | Click the chat icon from any screen |
| Phone | 1-800-HERO-FSM |
| Hours | Monday–Friday, 8am–6pm ET |

For security concerns specifically, email **security@officehero.dev** — we respond to every security report within 24 hours.
