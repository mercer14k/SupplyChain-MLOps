# Roadmap

The production-quality core is a tested single-node reference, with explicit environmental checks outstanding in the release checklist. Stretch deployments wait until those checks pass.

1. **Rolling-origin and segment evaluation.** Add intermittent-demand baselines, multiple cutoff dates, per-SKU gate thresholds and service-level-weighted loss. Acceptance: no fitting sees future actuals and a poor segment cannot pass through pooled accuracy alone.
2. **Scalable persistence.** Add PostgreSQL migrations, streaming JSONL validation, content-addressed object storage, SQL pagination and artifact retention. Acceptance: concurrent independent workers preserve idempotency and rollback during fault injection; backup/restore recovers checksummed artifacts.
3. **Champion/challenger serving.** Shadow predictions, delayed actual ingestion, accuracy/coverage monitoring and controlled traffic cohorts. Acceptance: exact version lineage for each request and one-step traffic rollback.
4. **Workload-aware orchestration.** Lease renewal, cancellation, queue/resource limits and Prefect/Airflow adapter. Acceptance: crashed/slow workers cannot double-register or starve API reads; schedules never bypass review.
5. **Independent identity and signed evidence.** OIDC reviewers, scoped credentials, artifact attestations and externally protected audit storage. Acceptance: approval requires a separately authenticated person and tampering is detectably rejected.

Later stretch work: Kubernetes manifests, feature registry, champion/challenger automation and lineage integration. None is claimed as implemented here.
