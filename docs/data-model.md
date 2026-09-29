# Data model

SQLite schema version 1 is created idempotently on startup. Future schema changes require an explicit migration; do not edit existing versioned databases in place without one.

| Collection | Key | Stored evidence |
|---|---|---|
| datasets | `ds-<raw hash prefix>` | raw SHA-256, canonical fingerprint, validated observations, full row validation report, source counts |
| jobs | generated job ID | typed training request, actor, status, attempt count, lease, run ID/error |
| runs | job-derived run ID | task/stage, dataset/code/artifact hashes, environment, parameters, metrics, gate, artifact, holdout chart, approval |
| deployments | task | serving run ID, updated timestamp |
| events | generated event ID | timestamp, event type, actor, object references, reason and transition evidence |
| predictions | generated prediction ID | serving run, dataset/artifact/input fingerprints and computed results |
| monitors | generated monitor ID | deployed version, evaluated dataset fingerprint, reference/current distributions, thresholds, alerts |
| schedules | generated schedule ID | pinned dataset/task, interval, next due UTC timestamp, enabled state, last job |
| idempotency | request key | scope/body fingerprint and original response |

Every observation has a stable ID, source ID, ingestion timestamp, `valid` status and lineage. Invalid lines have line number, raw hash, bounded preview and reason. Raw input bytes are fingerprinted but the complete original file is not retained; retain your source externally if forensic reconstruction of rejected records is required. This is explicit in the validation UI.

Artifacts contain only data: coefficients or robust centers/scales, calibration values, reference histograms, split boundaries, parameter/seed configuration, Python/NumPy version, algorithm revision, source-code hash and dataset fingerprint. No pickle loading or imported model execution exists.

Stage transitions: candidate → approved → production → archived. An archived, approved model may be deployed again. The rollback endpoint further checks that it appeared in prior deployment history. Training evidence is immutable through the API; stage and approval metadata are changed only by application services.

Time-sensitive operations use UTC ISO-8601 timestamps. UI timestamps are rendered in the viewer's local timezone. The native store is intentionally compact; for large datasets, migrate row/artifact storage and SQL-level pagination together.
