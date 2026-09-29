# Release checklist

This checklist separates implemented/verified work from environmental checks. Do not replace unchecked items with a blanket “production ready” claim.

## Verified locally

- [x] Working forecasting and anomaly training with chronological evaluation.
- [x] Stable synthetic generator, ConsignAI provenance and deliberately invalid fixture.
- [x] Registry, independent approval gate, atomic deployment and exact-output rollback.
- [x] Persistent schedules and worker crash-lease recovery tests.
- [x] Real API/database integration and full browser lifecycle with role changes.
- [x] AI disabled by default; no selected model; model failure cannot change deterministic state.
- [x] Schema, malformed-input, missing-evidence and computational regression tests.
- [x] Frontend lint, typecheck, unit tests, production build and mobile navigation.
- [x] Actual JSON/CSV/Markdown benchmark outputs with hardware/configuration.
- [x] Screenshots captured from the running application.
- [x] Documentation, source license, dependency inventory, security model and contribution files.

## Complete before public release claims

- [ ] Run `docker compose up --build --wait` on a machine with a container runtime; verify credentials, both candidates, inference and persistence after restart. Docker is not installed on this build machine.
- [ ] Push the local repository to the intended GitHub destination and wait for all CI jobs. No remote repository was created or published by this local-only delivery.
- [ ] Inspect the container vulnerability scan and resolve findings or document justified exceptions. The workflow exists; its remote result is not yet available.
- [ ] Verify native Windows startup on a Windows machine. Instructions are provided, not claimed as tested here.
- [ ] If enabling optional AI, test the chosen local model/runtime, record model license/config and inspect evidence citations. No live model was used for this build.
- [ ] Enable GitHub private vulnerability reporting, set maintainer contact and add repository topics/social metadata if desired.
- [ ] Review the final source-only archive/commit for secrets, private data and stale URLs.

The model core, native demo and lifecycle tests are delivered. Container execution, remote CI and optional live-model verification remain explicit environment-dependent checks.
