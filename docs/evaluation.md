# Evaluation

Run `python -m scml.evaluation.benchmark`. Outputs: `output/benchmark/results.json`, `results.csv`, `summary.md`. The harness raises a failure if any lifecycle assertion fails; it does not just print optimistic labels.

## Forecast protocol

All series share global date boundaries: first 65% of dates for fitting, next 15% for calibration, last 20% for holdout. Each series needs at least 28 uncensored fitting observations; datasets need at least 60 dates. Features are an intercept, normalized elapsed time, six weekday indicators and a planned-promotion indicator. Ridge regularizes all coefficients except the intercept. Predictions are clamped at zero.

Stockout days are excluded from fitting, residual calibration and holdout scoring because observed sales may censor true demand. Lost demand is not reconstructed. The baseline freezes the final pre-holdout observation for the same series/weekday; it never reads future holdout outcomes. WAPE uses `sum(abs(actual-predicted))/max(sum(actual),1)`. MAE, bias, holdout count and interval coverage are also stored.

The forecast gate requires WAPE <= 0.35 and WAPE <= max(0.05, 1.1 × weekly baseline WAPE). This is a transparent fixture policy, not a universal supply-chain service-level target. Calibration uses a finite-sample-adjusted 90th percentile of pooled absolute residuals. Serial dependence and heterogeneous SKUs invalidate any distribution-free coverage claim; reported holdout coverage is empirical.

## Anomaly protocol

The detector learns per-series median and MAD scales for lead time and fulfillment rate; scale floors are 0.25 days and 0.005 fulfillment units. Score is maximum absolute standardized deviation. A separate calibration window sets the threshold to max(3.5, median score + 6 × 1.4826 × score MAD), resisting anomalous calibration points.

Ground-truth labels are read only after fitting/calibration to evaluate holdout precision, recall and F1. The gate requires labeled evidence, F1 >= 0.75 and 0 < alert rate < 0.25. Missing labels block anomaly promotion. Deliberately large synthetic anomalies make this a recovery/infrastructure test, not an estimate of real-world detection quality.

## Lifecycle assertions

Two pipelines reproduce the same artifact hash across repeated fits in the same Python/NumPy environment. A different platform or BLAS may change floating-point bytes; bitwise portability is not promised. The benchmark then ingests a real fixture, trains and independently approves a baseline, deploys and calls inference, trains/deploys a challenger with alpha 2, rolls back and checks exact predictions/artifact hash. It verifies dataset lineage, a shifted-batch drift alert, serving API behavior and the rollback audit event.

PSI uses fit-reference quantile bins, finite outer bounds and additive 0.5 smoothing. PSI > 0.25 or standardized mean change > 3 alerts; a minimum of 30 current rows is required. A scale floor detects mean shifts for constant reference features. Histogram shape sensitivity is limited on degenerate data. Seasonal mix can produce false positives; this is not a significance test or causal accuracy monitor.

## Performance

`python scripts/performance.py --series 40 --days 365 --repeats 3` measures the same lifecycle on 14,600 rows. Fit min/median/max are separate from full harness time. Peak RSS is process-wide and includes imports/API smoke work, not per-model allocation. CPU name is recorded when the OS allows it; otherwise the limitation is explicit. All seeds, versions, dataset fingerprints and model hashes are recorded.

Committed results are actual runs on the build machine. They exclude Docker startup, cold dependency installation, GPU performance and live local-model generation. Benchmarks are not CI latency thresholds because hardware varies.
