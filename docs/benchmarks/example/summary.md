# Measured local benchmark

Measured: 2026-09-28T03:34:21.036573+00:00

Hardware: Apple M5 · macOS-26.6.2-arm64-arm-64bit · Python 3.12.14 · NumPy 2.5.3

Dataset: 720 observations, 4 SKU/location series, 180 days. Seed 42. Local AI disabled.

| Pipeline | Median training | Quality |
|---|---:|---:|
| Forecast | 1.732 ms | WAPE 3.9407% (baseline 7.9559%) |
| Anomaly | 0.780 ms | F1 1.0000 |

5 repeats per pipeline; complete harness 0.092 s; process peak RSS 70.7 MiB.

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
