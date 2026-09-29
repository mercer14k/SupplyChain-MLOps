# Architecture

SupplyChain MLOps is a local, single-node model lifecycle reference implementation. It separates HTTP contracts, application state transitions, numerical algorithms, local data, optional narrative generation and UI presentation.

## Ownership boundaries

- `domain/models.py`: pure NumPy fitting, prediction, calibration, scoring and drift. No database, HTTP or LLM calls.
- `domain/schemas.py`: Pydantic contracts and bounded fields; `errors.py`: typed domain failures.
- `data/generator.py`: reproducible fixtures and the actual ConsignAI adapter.
- `data/store.py`: SQLite WAL schema, parameterized writes, explicit `BEGIN IMMEDIATE`, read-only query connections.
- `services/ingestion.py`: validation reports and raw/canonical fingerprints; invalid source rows are never silently accepted.
- `services/lifecycle.py`: transactional idempotency, job leases, approval, deployment, inference, monitoring and scheduling.
- `ai/runtime.py`: a read-only local runtime interface and strict output/citation validation.
- `apps/api/main.py`: HTTP transport, auth, error conversion, trace logging and thin service dispatch.
- `apps/web`: a React operations workspace with live data and explicit empty/error states.

## Core workflow

Imports are versioned by the raw payload SHA-256. Canonical validated records are independently fingerprinted after sorting by stable record ID. Any invalid row makes that version ineligible for training; its report remains queryable.

Training is queued transactionally. The worker claims a queued job with a ten-minute lease and fits outside the write transaction. It only commits results if it still owns that lease. Expired claims can retry up to three times. A crash after artifact computation but before the commit causes recomputation; the job-derived run ID prevents duplicate run registration. The current implementation does not renew leases: restrict jobs to short, bounded local workloads or extend this mechanism before scaling.

A run stores its entire JSON artifact in the same database as its metrics and hashes. Approval requires passing the quality policy and a reviewer different from the training actor. Deployment uses an expected-current version; a stale caller receives a conflict. Archiving the old run, updating the pointer and recording the audit event commit together. Rollback additionally requires past deployment evidence.

Inference resolves the deployment pointer in a transaction, checks the artifact hash, computes predictions and records lineage. An idempotent retry returns the original result even if the deployment has subsequently changed. Model exports never deserialize executable objects.

Schedules are durable interval schedules in UTC, bound to a dataset version. Missed ticks coalesce, and an unresolved scheduled job prevents another enqueue. A schedule cannot approve a model. Monitoring is explicit batch evaluation against the stored fit reference; an alert is evidence for investigation, not automatic promotion.

## Operational topology

`web` serves static assets and proxies API calls; `api` serves typed endpoints; `worker` handles training/schedule ticks. API and worker share a named local SQLite volume. Only loopback ports 5188 and 8018 are published. Backend containers run as UID 10001 with a read-only root filesystem and a writable state volume.

Model summaries are audit aids, never a source of numerical or workflow truth. All numeric outputs derive from code and persisted models. No cloud AI or telemetry vendor is required.

## Deliberate limits

This is not a distributed registry, an MLflow-compatible service, or a replacement for platform identity and secret management. SQLite serializes writers; collection pagination is in memory; there is no retention policy, live feature store, distributed task queue or cross-host lease clock coordination. See the ADRs and roadmap for migration paths.
