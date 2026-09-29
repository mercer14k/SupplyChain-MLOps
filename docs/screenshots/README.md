# Reproduce the screenshots

Committed PNGs are captured from the real local application by `apps/web/e2e/lifecycle.spec.ts`. They contain synthetic data only.

1. Install the native backend and frontend dependencies as in `docs/development.md`.
2. In `apps/web`, run `pnpm exec playwright install chromium`.
3. Run `pnpm test:e2e`. The test starts isolated API/worker processes at port 8019 and a frontend at 5189; normal demo ports remain separate.
4. Desktop capture: 1512 × 982 viewport, full-page screenshot, `overview.png` and `monitoring.png`. Mobile capture: 390 × 844, full-page `mobile.png`.
5. Inspect the images before committing. Do not include access dialogs, secrets, runtime files or private source data.

The overview shows real seeded candidates; monitoring is captured after actual approval, deployment and shifted-batch evaluation. Browser test state can accumulate between runs, so counters/run IDs may differ. Screenshots are examples, not hard-coded UI fixtures. The local app preview runs at `http://127.0.0.1:5188`.
