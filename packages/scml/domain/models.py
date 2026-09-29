"""Interpretable, JSON-serializable statistical models. No executable artifacts."""

import hashlib
import platform
from collections import defaultdict
from datetime import date

import numpy as np

from scml.data.store import encode
from scml.domain.errors import DomainError

ALGORITHM_VERSION = "2026-09-v1"
FEATURES = ["lead_time_days", "fulfillment_rate"]


def series_key(r):
    return r["sku"] + "|" + r["location"]


def x(row, origin):
    d = date.fromisoformat(str(row["day"]))
    return [
        1.0,
        (d - date.fromisoformat(origin)).days / 100.0,
        *[float(d.weekday() == i) for i in range(6)],
        float(row["promotion"]),
    ]


def forecast_value(artifact, row):
    key = series_key(row)
    if key not in artifact["series"]:
        raise DomainError("No trained evidence for this SKU/location", "missing_evidence", 422)
    model = artifact["series"][key]
    return max(0.0, float(np.dot(x(row, artifact["origin"]), model["coefficients"])))


def anomaly_score(artifact, row):
    key = series_key(row)
    if key not in artifact["series"]:
        raise DomainError("No trained evidence for this SKU/location", "missing_evidence", 422)
    m = artifact["series"][key]
    scores = [abs(row[f] - m["center"][i]) / m["scale"][i] for i, f in enumerate(FEATURES)]
    return max(scores)


def profile(values):
    values = np.asarray(values, dtype=float)
    edges = np.unique(np.quantile(values, np.linspace(0, 1, 11))).tolist()
    edges = [-1e15, *edges[1:-1], 1e15]
    counts, _ = np.histogram(values, bins=edges)
    return {
        "edges": edges,
        "counts": counts.tolist(),
        "n": len(values),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
    }


def drift(reference, current):
    if len(current) < 30:
        raise DomainError(
            "At least 30 observations are required for drift evidence", "missing_evidence", 422
        )
    counts, _ = np.histogram(current, bins=reference["edges"])
    p = (np.asarray(reference["counts"]) + 0.5) / (reference["n"] + len(counts) * 0.5)
    q = (counts + 0.5) / (len(current) + len(counts) * 0.5)
    psi = float(np.sum((q - p) * np.log(q / p)))
    # Constant reference distributions need a location test as well as histogram PSI.
    shift = abs(float(np.mean(current)) - reference["mean"]) / max(reference["std"], 0.01)
    return {
        "psi": psi,
        "mean_shift_std": shift,
        "alert": psi > 0.25 or shift > 3,
        "reference_n": reference["n"],
        "current_n": len(current),
        "reference_counts": reference["counts"],
        "current_counts": counts.tolist(),
        "edges": reference["edges"],
        "current_mean": float(np.mean(current)),
        "reference_mean": reference["mean"],
    }


def train(records, task, seed=42, ridge_alpha=1.0):
    rows = sorted(records, key=lambda r: (r["day"], r["sku"], r["location"], r["id"]))
    days = sorted({r["day"] for r in rows})
    if len(days) < 60:
        raise DomainError("Training requires at least 60 distinct days", "insufficient_data", 422)
    fit_end, calibration_end = days[int(len(days) * 0.65) - 1], days[int(len(days) * 0.8) - 1]
    fit = [r for r in rows if r["day"] <= fit_end and not r["stockout"]]
    calibration = [r for r in rows if fit_end < r["day"] <= calibration_end]
    test = [r for r in rows if r["day"] > calibration_end]
    groups = defaultdict(list)
    for r in fit:
        groups[series_key(r)].append(r)
    if any(len(rs) < 28 for rs in groups.values()) or not groups:
        raise DomainError(
            "Every series needs 28 uncensored training observations", "insufficient_data", 422
        )
    if {series_key(r) for r in rows} != set(groups):
        raise DomainError("A series has no uncensored training history", "missing_evidence", 422)
    artifact = {
        "format": 1,
        "algorithm_version": ALGORITHM_VERSION,
        "task": task,
        "origin": days[0],
        "train_end": fit_end,
        "calibration_end": calibration_end,
        "data_end": days[-1],
        "series": {},
        "seed": seed,
        "parameters": {
            "ridge_alpha": ridge_alpha,
            "fit_fraction": 0.65,
            "calibration_fraction": 0.15,
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
    }
    if task == "forecast":
        for key, rs in groups.items():
            a = np.asarray([x(r, days[0]) for r in rs])
            y = np.asarray([r["demand"] for r in rs])
            regularizer = np.eye(a.shape[1]) * ridge_alpha
            regularizer[0, 0] = 0
            coefficients = np.linalg.solve(a.T @ a + regularizer, a.T @ y)
            artifact["series"][key] = {"coefficients": coefficients.tolist(), "n": len(rs)}
        residuals = [
            abs(r["demand"] - forecast_value(artifact, r)) for r in calibration if not r["stockout"]
        ]
        if not residuals:
            raise DomainError("No uncensored calibration evidence", "missing_evidence", 422)
        artifact["interval_q90"] = float(
            np.quantile(
                residuals,
                min(1.0, np.ceil((len(residuals) + 1) * 0.9) / len(residuals)),
                method="higher",
            )
        )
        observed = [r for r in test if not r["stockout"]]
        if not observed:
            raise DomainError("No uncensored holdout evidence", "missing_evidence", 422)
        actual = np.asarray([r["demand"] for r in observed])
        pred = np.asarray([forecast_value(artifact, r) for r in observed])
        # Frozen-origin weekly baseline uses the final pre-holdout value for each weekday.
        previous = {
            (series_key(r), date.fromisoformat(r["day"]).weekday()): r["demand"]
            for r in rows
            if r["day"] <= calibration_end and not r["stockout"]
        }
        if any(
            (series_key(r), date.fromisoformat(r["day"]).weekday()) not in previous
            for r in observed
        ):
            raise DomainError(
                "Weekly baseline lacks historical weekday evidence", "missing_evidence", 422
            )
        baseline = np.asarray(
            [previous[(series_key(r), date.fromisoformat(r["day"]).weekday())] for r in observed]
        )
        denom = max(float(actual.sum()), 1.0)
        metrics = {
            "wape": float(np.abs(actual - pred).sum() / denom),
            "mae": float(np.abs(actual - pred).mean()),
            "bias": float((pred - actual).sum() / denom),
            "baseline_wape": float(np.abs(actual - baseline).sum() / denom),
            "interval_coverage": float((np.abs(actual - pred) <= artifact["interval_q90"]).mean()),
            "holdout_n": len(observed),
        }
        gate = metrics["wape"] <= 0.35 and metrics["wape"] <= max(
            0.05, metrics["baseline_wape"] * 1.1
        )
        chart = [
            {
                "day": r["day"],
                "sku": r["sku"],
                "location": r["location"],
                "actual": r["demand"],
                "prediction": round(float(v), 4),
            }
            for r, v in zip(observed, pred, strict=True)
        ]
        predict = forecast_value
    elif task == "anomaly":
        for key, rs in groups.items():
            matrix = np.asarray([[r[f] for f in FEATURES] for r in rs])
            center = np.median(matrix, axis=0)
            scale = np.maximum(np.median(abs(matrix - center), axis=0) * 1.4826, [0.25, 0.005])
            artifact["series"][key] = {
                "center": center.tolist(),
                "scale": scale.tolist(),
                "n": len(rs),
            }
        cal_scores = [anomaly_score(artifact, r) for r in calibration]
        cal_center = float(np.median(cal_scores))
        cal_mad = float(np.median(np.abs(np.asarray(cal_scores) - cal_center)))
        artifact["threshold"] = max(3.5, cal_center + 6 * 1.4826 * cal_mad)
        scores = [anomaly_score(artifact, r) for r in test]
        flags = [s > artifact["threshold"] for s in scores]
        truth = [r["is_anomaly"] for r in test]
        tp = sum(a and b for a, b in zip(flags, truth, strict=True))
        labeled = any(r["is_anomaly"] for r in rows)
        precision = tp / max(1, sum(flags))
        recall = tp / max(1, sum(truth))
        metrics = {
            "precision": precision if labeled else None,
            "recall": recall if labeled else None,
            "f1": 2 * precision * recall / max(1e-12, precision + recall) if labeled else None,
            "alert_rate": sum(flags) / len(flags),
            "holdout_n": len(test),
            "labeled": labeled,
        }
        gate = labeled and metrics["f1"] >= 0.75 and 0 < metrics["alert_rate"] < 0.25
        chart = [
            {
                "day": r["day"],
                "sku": r["sku"],
                "location": r["location"],
                "score": s,
                "flag": a,
                "truth": b,
            }
            for r, s, a, b in zip(test, scores, flags, truth, strict=True)
        ]
        predict = anomaly_score
    else:
        raise DomainError("Unsupported task", "validation", 422)
    artifact["reference"] = {f: profile([r[f] for r in fit]) for f in ["demand", *FEATURES]}
    artifact["reference"]["prediction"] = profile([predict(artifact, r) for r in fit])
    metrics["fit_n"] = len(fit)
    metrics["excluded_stockout_n"] = sum(r["stockout"] for r in rows)
    return (
        artifact,
        metrics,
        {
            "passed": bool(gate),
            "policy": "quality-v1",
            "reason": "Chronological holdout passed the task quality policy"
            if gate
            else "Quality policy failed or labeled anomaly evidence unavailable",
        },
        chart,
    )


def artifact_hash(artifact):
    return hashlib.sha256(encode(artifact).encode()).hexdigest()
