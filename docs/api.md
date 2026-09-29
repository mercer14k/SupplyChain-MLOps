# API guide

OpenAPI: `http://localhost:8018/docs`; schema: `/openapi.json`. API routes use `/api/v1`. Health and readiness are `/health` and `/ready`; readiness checks the database. The overview separately reports worker freshness.

Reads are unauthenticated on this loopback-bound local demo. Mutations require `Authorization: Bearer <role-token>` and an `Idempotency-Key` of 8–160 characters. The optional explanation endpoint requires a role token but no idempotency key because it changes no business state. Query pages use `limit` (1–100) and nonnegative `offset` and return items/total/limit/offset. Dataset lists support `q`; runs support `task` and `stage`.

| Operation | Endpoint | Role |
|---|---|---|
| Upload JSONL | POST `/datasets?filename=example.jsonl` | operator |
| Queue training | POST `/training` | operator |
| Poll a job | GET `/jobs/{id}` | read |
| Review evidence | GET `/runs/{id}` | read |
| Export JSON artifact | GET `/runs/{id}/artifact` | read |
| Approve | POST `/runs/{id}/approve` | reviewer |
| Deploy | POST `/deployments/{task}` | operator |
| Roll back | POST `/deployments/{task}/rollback` | operator |
| Forecast | POST `/predictions/forecast` | operator |
| Score anomalies | POST `/predictions/anomaly` | operator |
| Monitor a batch | POST `/monitors` | operator |
| Create schedule | POST `/schedules` | operator |
| Pause/enable | POST `/schedules/{id}/enabled?enabled=false` | operator |
| Optional narrative | POST `/runs/{id}/explain` | either role |

Prefixes above are relative to `/api/v1`. Read collections also expose datasets, runs, jobs, predictions, monitors, schedules and events.

## Payloads

Training: `{"dataset_id":"ds-...","task":"forecast","seed":42,"ridge_alpha":1}`. Task is `forecast` or `anomaly`. Approval: `{"reason":"Reviewed holdout metrics and provenance"}`. Deployment/rollback: `{"run_id":"run-...","expected_current":null,"reason":"Approved baseline deployment"}`. Use the current run ID instead of null after the first deployment. A changed pointer returns 409 rather than overwriting another operator's choice.

Forecast: `{"sku":"SKU-001","location":"CHI","start":"2025-06-30","horizon":14,"promotion":false}` for the default fixture. Start must be after the source dataset's last date, and the last requested date must be within 90 days of that date. Unknown series receive `missing_evidence`, never a guessed fallback. Anomaly inference accepts `{"observations":[<canonical observations>]}` up to 500 records.

Monitoring: `{"task":"forecast","dataset_id":"ds-..."}`. Schedules add `interval_minutes` (at least 5), seed and enabled flag. Pinned versions prevent silent data changes. Schedule updates currently toggle enabled state; create a new schedule when changing its dataset.

Upload uses raw UTF-8 JSONL with `Content-Type: application/x-ndjson` (or `application/jsonl`) and at most 16 MiB/100,000 lines. It is not multipart/form-data. Invalid records produce a stored report and HTTP 201 for the imported quarantined version. They cannot be trained. Malformed transport/oversized bodies return 4xx. Export returns validated rows only and does not reconstruct the rejected raw file.

## Error and retry semantics

```json
{"error":{"code":"stale_deployment","message":"Deployment changed. Refresh and review before retrying.","trace_id":"...","details":[]}}
```

The trace also appears as `X-Trace-ID`. Reuse a mutation's idempotency key for transport retries with the same body/actor/scope. A different body under that key returns 409. The UI creates a new key for a deliberate new action. Request validation errors have field-level details. Job failures persist a safe message; unexpected exception details stay out of client responses.
