# Screenshots

This directory holds rendered UI screenshots. They refresh through **two**
automated paths so the committed PNGs always match the rendered app:

1. **Git-hook build pipeline (local):** `.githooks/pre-push` runs
   [`scripts/capture-screenshots.sh`](../../scripts/capture-screenshots.sh)
   whenever a push touches `apps/admin-web/` or the shared packages. Fresh
   PNGs are written here and staged; if anything changed the push aborts so
   the refreshed screenshots ride the next commit. Skip with
   `OFFICE_HERO_SKIP_SCREENSHOTS=1 git push`.
2. **CI backstop:** the [`ui-screenshots`](../../.github/workflows/ui-screenshots.yml)
   workflow re-captures on PRs (artifact + sticky comment) and on pushes to
   `main` (commits refreshed PNGs back with `[skip ci]`).

## Layout

```
docs/screenshots/
└── admin-web/
    ├── desktop/   # 1280 × 800
    │   ├── 01-login.png
    │   ├── 02-jobs.png
    │   ├── 03-dispatch.png
    │   ├── 04-vehicles.png
    │   ├── 05-users.png
    │   ├── 06-customers.png
    │   ├── 07-contracts.png
    │   └── 08-routes.png
    └── mobile/    # 375 × 812 (same eight routes)
```

## Generating locally

```bash
bash scripts/capture-screenshots.sh        # boots vite itself, writes here
# or, route-by-route iteration:
cd apps/admin-web && pnpm screenshots      # writes apps/admin-web/screenshots/
```

One-time prerequisite: `npx playwright install chromium`.

## Bypassed auth

The screenshot spec seeds `localStorage` with a fake bearer token so it can capture authenticated routes without a running backend. Data-driven sections show error or empty states (this is intentional — the goal is UI shell ground-truth, not data fidelity).

## Caveats

- Screenshots are deterministic *enough* for visual review but include a brief 250ms settle delay; flaky pixel comparisons are not recommended. Use these for human review, not pixel-diff regressions.
- The desktop viewport is 1280×800; if you change it in [`screenshots.spec.ts`](../../apps/admin-web/src/e2e/screenshots.spec.ts), update this README too.
