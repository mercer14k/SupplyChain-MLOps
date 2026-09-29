# ADR 001: transactional local registry and persistent worker

Status: accepted for the reference implementation.

The requested MLOps lifecycle matters more than deploying many services in a portfolio demo. Use SQLite WAL for datasets, experiment evidence, artifacts, registry stages, deployment pointers, audit events, schedules and idempotency. A small Python worker claims durable jobs and runs interval schedules.

This replaces the recommended MLflow, DVC/lakeFS, Prefect/Airflow, PostgreSQL and MinIO components in the default stack. It reduces startup cost and keeps the critical state transition and recovery behavior inspectable. No third-party API compatibility is claimed. Raw/canonical fingerprints provide local dataset versioning, not remote DVC semantics.

Costs: single-node writer serialization, in-memory JSON collections, no warehouse scale, no rich workflow DAGs, no cross-machine clock coordination, no externally protected audit history. Migration should first move model/data blobs to content-addressed storage, metadata to PostgreSQL with migrations, and orchestration to a workflow engine without weakening promotion rules. See roadmap.
