# Screenshots

This directory holds rendered UI screenshots, refreshed automatically by the [`ui-screenshots`](../../.github/workflows/ui-screenshots.yml) workflow whenever the admin-web (or its packages) changes on `main`.

## Layout

```
docs/screenshots/
└── admin-web/
    ├── desktop/   # 1280 × 800
    │   ├── 01-login.png
    │   ├── 02-jobs.png
    │   ├── 03-dispatch.png
    │   ├── 04-vehicles.png
    │   └── 05-users.png
    └── mobile/    # 375 × 812
        ├── 01-login.png
        ├── 02-jobs.png
        ├── 03-dispatch.png
        ├── 04-vehicles.png
        └── 05-users.png
```

## When these update

- **On PR:** the [`UI Screenshots`](../../.github/workflows/ui-screenshots.yml) workflow runs against the PR branch, uploads a fresh set as a workflow artifact, and posts a sticky comment with the artifact link. The files in `docs/screenshots/` itself are *not* updated until merge.
- **On push to `main`:** the same workflow re-runs and commits the refreshed PNGs back to `docs/screenshots/admin-web/` with `[skip ci]` so the workflow doesn't loop.

## Generating locally

```bash
cd apps/admin-web
pnpm dev                                                # in one shell
SCREENSHOT_DIR=screenshots npx playwright test \
    src/e2e/screenshots.spec.ts --project=chromium       # in another
```

Output: `apps/admin-web/screenshots/{desktop,mobile}/*.png`.

To preview a doc-style refresh (without committing): copy those into `docs/screenshots/admin-web/` and diff.

## Bypassed auth

The screenshot spec seeds `localStorage` with a fake bearer token so it can capture authenticated routes without a running backend. Data-driven sections show error or empty states (this is intentional — the goal is UI shell ground-truth, not data fidelity).

## Caveats

- Screenshots are deterministic *enough* for visual review but include a brief 250ms settle delay; flaky pixel comparisons are not recommended. Use these for human review, not pixel-diff regressions.
- The desktop viewport is 1280×800; if you change it in [`screenshots.spec.ts`](../../apps/admin-web/src/e2e/screenshots.spec.ts), update this README too.
