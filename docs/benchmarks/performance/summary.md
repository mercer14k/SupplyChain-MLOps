# Measured local benchmark

Measured: 2026-09-28T03:34:22.012045+00:00

Hardware: Apple M5 · macOS-26.6.2-arm64-arm-64bit · Python 3.12.14 · NumPy 2.5.3

Dataset: 14,600 observations, 40 SKU/location series, 365 days. Seed 42. Local AI disabled.

| Pipeline | Median training | Quality |
|---|---:|---:|
| Forecast | 39.935 ms | WAPE 0.7720% (baseline 1.7527%) |
| Anomaly | 15.170 ms | F1 1.0000 |

3 repeats per pipeline; complete harness 0.781 s; process peak RSS 161.8 MiB.

## Lifecycle assertions

- [x] forecast reproducible
- [x] forecast quality gate
- [x] anomaly reproducible
- [x] anomaly quality gate
- [x] rollback exact predictions
- [x] rollback exact artifact
- [x] dataset traceability
- [x] drift alert
- [x] deployment api smoke
- [x] rollback audit

Synthetic local single-process benchmark. RSS includes imports and the API smoke test; not an isolated model allocation. No Docker or live LLM benchmark.

Re-run with `python -m scml.evaluation.benchmark`. Performance varies with hardware and background load. Synthetic quality is not a production accuracy claim.
