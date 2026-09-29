import copy
import math

import pytest
from scml.data.generator import generate
from scml.domain.errors import DomainError
from scml.domain.models import anomaly_score, artifact_hash, drift, forecast_value, profile, train


def test_fixed_seed_generator():
    assert list(generate(42)) == list(generate(42))
    assert list(generate(42)) != list(generate(43))


@pytest.mark.parametrize("task", ["forecast", "anomaly"])
def test_reproducible_training(records, task):
    a, m, g, _ = train(records, task)
    b, m2, g2, _ = train(records[::-1], task)
    assert artifact_hash(a) == artifact_hash(b)
    assert m == m2 and g == g2
    assert g["passed"]


def test_forecast_beats_baseline(records):
    artifact, metrics, gate, chart = train(records, "forecast")
    assert metrics["wape"] < metrics["baseline_wape"] and metrics["wape"] < 0.1
    assert artifact["train_end"] < artifact["calibration_end"] < min(r["day"] for r in chart)
    assert gate["passed"]


def test_holdout_cannot_change_fitted_parameters(records):
    a, _, _, _ = train(records, "forecast")
    changed = copy.deepcopy(records)
    for r in changed:
        if r["day"] > a["calibration_end"]:
            r["demand"] *= 5
    b, _, _, _ = train(changed, "forecast")
    assert a["series"] == b["series"] and a["interval_q90"] == b["interval_q90"]


def test_anomaly_labels_never_enter_fit(records):
    a, _, _, _ = train(records, "anomaly")
    changed = [{**r, "is_anomaly": not r["is_anomaly"]} for r in records]
    b, _, _, _ = train(changed, "anomaly")
    assert artifact_hash(a) == artifact_hash(b)


def test_anomaly_threshold_resists_calibration_contamination(records):
    _, metrics, gate, _ = train(records, "anomaly")
    assert metrics["recall"] == 1 and metrics["precision"] >= 0.8 and gate["passed"]


def test_unlabeled_anomaly_is_not_approvable(records):
    _, metrics, gate, _ = train([{**r, "is_anomaly": False} for r in records], "anomaly")
    assert metrics["f1"] is None and not gate["passed"]


def test_zero_demand_metrics_are_finite(records):
    _, metrics, _, _ = train([{**r, "demand": 0} for r in records], "forecast")
    assert all(math.isfinite(v) for v in metrics.values())
    assert metrics["wape"] == 0


def test_stockout_censoring(records):
    records[0]["stockout"] = True
    _, metrics, _, _ = train(records, "forecast")
    assert metrics["excluded_stockout_n"] == 1 and metrics["fit_n"] == 467


def test_missing_series_abstains(records):
    a, _, _, _ = train(records, "forecast")
    with pytest.raises(DomainError, match="No trained evidence"):
        forecast_value(a, {**records[0], "sku": "UNKNOWN"})


def test_insufficient_history(records):
    with pytest.raises(DomainError, match="60 distinct days"):
        train(records[:30], "forecast")


def test_drift_equal_and_shifted():
    ref = profile(list(range(100)))
    assert not drift(ref, list(range(100)))["alert"]
    assert drift(ref, list(range(200, 300)))["alert"]


def test_constant_feature_drift():
    assert drift(profile([1.0] * 100), [4.0] * 100)["alert"]
    assert not drift(profile([1.0] * 100), [1.0] * 100)["alert"]


def test_missing_drift_evidence():
    with pytest.raises(DomainError, match="30 observations"):
        drift(profile([1, 2, 3]), [1, 2])


def test_anomaly_prediction_no_labels(records):
    a, _, _, _ = train(records, "anomaly")
    r = records[0]
    assert anomaly_score(a, r) == anomaly_score(a, {**r, "is_anomaly": not r["is_anomaly"]})


def test_missing_baseline_weekday_evidence(records):
    from datetime import date

    filtered = [
        r
        for r in records
        if not (
            r["sku"] == "SKU-001"
            and r["day"] <= "2025-05-24"
            and date.fromisoformat(r["day"]).weekday() == 0
        )
    ]
    with pytest.raises(DomainError, match="weekday evidence"):
        train(filtered, "forecast")
