---
docType: tasks
layer: project
audience: [human, ai]
description: Ongoing maintenance tasks and one-time dev environment setup
dateCreated: 20260308
dateUpdated: 20260308
status: in_progress
---

# 950: Maintenance & Dev Environment Setup Tasks

Operational tasks not tied to a specific feature slice. See `file-naming-conventions.md`
for the 950-999 maintenance range.

---

## DEV-01: Android Emulator Setup

**Owner:** Human (Jake) or dedicated context session
**Objective:** Install Android Studio + Android Virtual Device (AVD) on this
machine so Maestro E2E tests can run against an Android emulator.

**Steps:**

- [ ] Download and install Android Studio
  (<https://developer.android.com/studio>)
- [ ] During setup: install Android SDK, Android SDK Platform (API 33+), Android
  Emulator, Android SDK Platform-Tools
- [ ] Open AVD Manager → Create Virtual Device
  - Device: Pixel 7 (or equivalent)
  - System image: API 33 (Android 13) x86\_64
  - RAM: 2048 MB minimum
- [ ] Start emulator and verify: `adb devices` shows a running device
- [ ] Install Expo Go on the emulator (via Play Store or APK side-load)
- [ ] Run `npx expo start --android` from `apps/tech-mobile/` to verify app loads
- [ ] Install Maestro CLI: `curl -Ls "https://get.maestro.mobile.dev" | bash`
- [ ] Run smoke test: `maestro test .maestro/smoke.yaml`

**Success Criteria:**

- [ ] `adb devices` shows at least one running emulator
- [ ] Office Hero app loads on the emulator from Expo dev server
- [ ] Maestro smoke test passes (basic navigation)

---

## DEV-02: iOS Simulator Setup

**Owner:** Human (Jake) — requires macOS
**Objective:** Install Xcode + iOS Simulator for iOS E2E tests.

**Note:** iOS Simulator requires macOS. This task is deferred until iOS
support is enabled in the React Native Expo build (see Future Work in slice plan).

**Steps:**

- [ ] Install Xcode from Mac App Store (latest stable)
- [ ] Open Xcode → Preferences → Components → Download iOS 17+ simulator
- [ ] Open Simulator app → Device → iPhone 15 (or equivalent)
- [ ] Run `npx expo start --ios` from `apps/tech-mobile/` to verify app loads
- [ ] Install Maestro CLI (if not already installed from DEV-01)
- [ ] Run iOS smoke test: `maestro test --device ios .maestro/smoke.yaml`

**Success Criteria:**

- [ ] iOS Simulator launches successfully
- [ ] Office Hero app loads in iOS Simulator
- [ ] Maestro smoke test passes on iOS

---

## DEV-03: Grafana/Loki Observability Setup

**Owner:** AI or human
**Objective:** Connect Fly.io log output to Grafana Cloud for Operator
dashboard and log viewer (see spec Operator Dashboard section).

**Steps:**

- [ ] Create Grafana Cloud account (free tier: <https://grafana.com/products/cloud/>)
- [ ] In Grafana Cloud: create a Loki data source, note the push URL + API key
- [ ] Configure Fly.io log shipper to forward to Loki:

  ```toml
  # In fly.toml [log] or via fly logs --json | ...
  ```

  Fly.io supports log shipping via Vector or external log drains.
- [ ] Import pre-built FastAPI dashboard from Grafana marketplace (search: "FastAPI")
- [ ] Create custom dashboard panels:
  - Uptime (from `/health` probe frequency)
  - API p50/p95/p99 (from structlog `duration_ms` field)
  - Error rate (from `level=error` log count)
  - Dead-letter count (from `event_type=dead_letter` audit log count)
- [ ] Configure Sentry (free tier: <https://sentry.io>):
  - Create project → get DSN → set `SENTRY_DSN` in Fly.io secrets
  - Install `sentry-sdk[fastapi]` in production deps
- [ ] Set up Grafana alerting:
  - Dead-letter count > 0 → email alert
  - API error rate > 5% for 5 min → email alert

**Success Criteria:**

- [ ] Logs visible in Grafana Loki with `tenant_id`, `request_id` filters
- [ ] Dashboard shows uptime + response time metrics
- [ ] Audit log tab shows auth events
- [ ] Test alert fires successfully

---

## DEV-04: Context Forge (cf) CLI Setup

**Owner:** Human (Jake)
**Objective:** Install Context Forge CLI to unlock Claude Code slash commands.

**Steps:**

- [ ] Check if npm/pnpm global install is available
- [ ] Install: `npm install -g @context-forge/cli` (or check current install method
  at <https://github.com/ecorkran/context-forge>)
- [ ] In repo root: `cf init` (if not already done — submodule is present)
- [ ] Run: `cf install-commands` to install Claude Code slash commands
- [ ] Verify: in Claude Code, type `/` and check for cf-registered commands

**Success Criteria:**

- [ ] `cf --version` runs without error
- [ ] Claude Code shows cf slash commands in the `/` menu

---

## Recurring Maintenance

- [ ] Rotate JWT RS256 key pair annually (or immediately on suspected compromise)
- [ ] Review and prune dead-letter table monthly
- [ ] Audit `audit_events` table for anomalies monthly
- [ ] Update Python dependencies: `pip-audit` runs 4× daily but quarterly
  manual dependency review for major version updates
- [ ] Review Fly.io + Neon free tier limits as Tenant count grows
