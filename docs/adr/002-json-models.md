# ADR 002: explicit statistical models and JSON artifacts

Status: accepted.

Forecasting uses regularized calendar/promotion regression per SKU/location. Anomaly detection uses robust median/MAD deviations. Both are NumPy implementations with deterministic fitting, explicit features and chronological evaluation. Reference histograms implement custom drift checks.

These choices avoid requiring a large ML framework or Evidently server for this local example. Model artifacts are inspectable JSON rather than arbitrary Python pickle objects. SHA-256 verification checks consistency before serving. This is not a signature or a guarantee against an administrator rewriting the database.

Costs: baseline model expressiveness; empirical pooled intervals; no learned feature interactions, hierarchical reconciliation, seasonality beyond weekday/promotion/trend, or interchangeable sklearn estimator loading. More capable estimators should implement a typed safe artifact format and the same evaluation contract. See [scikit-learn persistence guidance](https://scikit-learn.org/stable/model_persistence.html) for executable-deserialization risks.
