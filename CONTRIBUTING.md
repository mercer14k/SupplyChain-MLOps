# Contributing

Start with a reproducible operational failure or clearly scoped improvement. Read the architecture and ADRs, then use the native development guide. Keep deterministic domain logic independent of routes/UI and make numerical changes reproducible with fixed seeds and chronological evaluation.

Before a pull request:

1. Run backend lint, formatting and pytest; run frontend lint, typecheck, unit tests and build.
2. Run the browser lifecycle suite for workflow/UI changes.
3. Run the benchmark for algorithm/artifact changes and explain metric shifts. Never hand-edit benchmark values.
4. Run dependency audits for lockfile changes; document material licenses.
5. Update schema, documentation and release checks when behavior changes.

Do not commit `.env`, `.runtime`, credentials, private data, model weights, screenshots of secrets or test traces. Use tiny synthetic fixtures with ground truth. Do not add paid/cloud AI requirements or auto-promotion. A PR should explain the problem, resulting behavior, validation and limitations. The project uses Apache-2.0; contributions are offered under that license unless otherwise discussed.
