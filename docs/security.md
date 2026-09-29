# Security and privacy

## Trust model

This is a local single-user/small-team reference system, not an internet-facing SaaS. Local administrators can inspect the database, tokens and model artifacts; they are inside the trust boundary. Imported data, filenames, HTTP inputs and local-model output are untrusted. Assets to protect include datasets, deployment state, model integrity and approval history.

| Threat | Implemented control | Remaining boundary |
|---|---|---|
| Unauthorized state mutation | Generated 256-bit role keys; server-side operator/reviewer dependencies; distinct role keys; no token in browser storage | Static local roles, not individual identity or SSO; host admin can read both keys |
| Approval bypass | Passing quality policy, different training/review actors, explicit approval before deployment | The operator can edit files on their own machine; no independent external auditor |
| Stale/retried deployment | Transactional idempotency and expected-current pointer checks | Keys currently retained indefinitely; no distributed transaction layer |
| Executable model artifact | Inspectable JSON and SHA-256 verification before approval/deployment/inference/export | Hashes are not signatures; a host admin can change artifact and stored hash |
| Invalid/hostile upload | 16-MiB bound, JSONL-only MIME and extension, typed finite ranges, duplicate detection, sanitized name, persisted rejection report | Rejected previews may contain sensitive source content; do not import secrets |
| SQL/command injection | Parameterized values; table names from an internal allowlist; no generated SQL or shell execution | Domain code is trusted and can use DB write connections |
| Prompt injection or model hallucination | Untrusted-evidence instructions, schema validation, evidence allowlist, labeled narrative, no model tools | Schema/citation validation cannot prove every sentence is true |
| Outbound data exfiltration | AI off by default; endpoint restricted to local names; no redirects, no proxy environment; no hosted analytics/fonts | An operator-controlled local runtime itself must not proxy to the cloud |
| Browser attacks | No raw HTML rendering; same-origin writes; trusted hosts; no cookie auth; bounded uploads; production CSP and frame denial | CSP allows inline styles for data-bound histogram heights; no third-party scripts |
| Resource abuse | Bounded upload/row/inference sizes; fit outside DB write lock; one durable worker | No API quotas, per-user throttling or multi-tenant isolation; keep loopback binding |

## Credentials

First startup creates `.runtime/credentials.json` (or `/state/credentials.json`) with mode 0600. `scml keys` intentionally displays local role keys for the operator. `.runtime`, `.env`, test traces and temporary outputs are ignored by Git and excluded from source archives. Configure distinct environment keys of at least 24 characters if overriding. Do not paste credentials into issues, screenshots or benchmark results.

## Storage and network

SQLite WAL with foreign keys and explicit write transactions is shared only by local backend processes. Read queries use read-only/query-only connections. Both Compose ports bind to 127.0.0.1. Backend containers run unprivileged with a read-only root filesystem and no additional capabilities. Nginx serves the built application and proxies API writes. No cloud telemetry is transmitted by the application.

Raw file hashes and bounded rejected-line previews are retained; full rejected files are not stored. Export and logs may reveal operational information. Use synthetic/public data for portfolio demos. There is no encryption-at-rest facility beyond your OS/filesystem; use an encrypted local disk when needed.

## Audit and observability

Structured HTTP logs include generated trace ID, path, method, status and latency. Training logs include run/dataset identifiers, duration and seed. Lifecycle events persist actors, references, reasons and transitions. LLM telemetry is observable configuration/validation data, never hidden reasoning. Tokens and raw request bodies are not logged. Events are append-only through the API, but not cryptographically tamper-evident.

## Verification and limitations

Tests cover auth boundaries, cross-origin rejection, invalid uploads, idempotency conflicts, stale deployment, artifact tampering, failed quality gates, missing evidence, read-only DB connections and LLM failure isolation. Dependency audits use pip-audit and pnpm audit; CI also scans container images with Trivy. Results apply to the scanned lockfiles and advisory database at run time, not a guarantee of no vulnerabilities.

Before exposing this beyond loopback, add independent identities, TLS/reverse-proxy hardening, quotas, retention, backup/restore drills, secret rotation and external audit protection. Container execution and live local-model generation still require verification on a suitable machine. Report issues through [SECURITY.md](../SECURITY.md).
