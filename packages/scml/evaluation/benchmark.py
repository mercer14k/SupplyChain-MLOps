"""One command measures and asserts the complete lifecycle against real artifacts."""

import argparse
import csv
import hashlib
import json
import os
import platform
import statistics
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import numpy as np
from fastapi.testclient import TestClient

from scml.data.generator import generate
from scml.data.store import Store
from scml.domain.models import artifact_hash, train
from scml.services.config import Settings
from scml.services.lifecycle import Lifecycle


def hardware():
    cpu = platform.processor() or platform.machine()
    if platform.system() == "Darwin":
        try:
            cpu = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            cpu += " (detailed CPU metadata unavailable)"
    return {
        "os": platform.platform(),
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "local_llm": "disabled",
        "seed": 42,
    }


def peak_memory():
    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return value / (1024 * 1024) if platform.system() == "Darwin" else value / 1024
    except ImportError:
        return None


def benchmark(output="docs/benchmarks/example", days=180, series=4, repeats=5):
    from apps.api.main import create_app

    start = time.perf_counter()
    rows = list(generate(42, days, series))
    encoded = "".join(
        json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows
    ).encode()
    timings = {}
    artifacts = {}
    quality = {}
    checks = {}
    for task in ("forecast", "anomaly"):
        samples = []
        hashes = []
        for _ in range(repeats):
            tick = time.perf_counter()
            artifact, metrics, gate, _ = train(rows, task)
            samples.append(time.perf_counter() - tick)
            hashes.append(artifact_hash(artifact))
        timings[task] = {
            "median_seconds": statistics.median(samples),
            "min_seconds": min(samples),
            "max_seconds": max(samples),
            "repeats": repeats,
        }
        checks[task + "_reproducible"] = len(set(hashes)) == 1
        checks[task + "_quality_gate"] = gate["passed"]
        artifacts[task] = hashes[0]
        quality[task] = metrics
    with tempfile.TemporaryDirectory() as directory:
        settings = Settings(directory)
        service = Lifecycle(Store(directory))
        ds = service.ingest(encoded, "benchmark.jsonl", "operator", uuid4().hex)
        request = {"dataset_id": ds["id"], "task": "forecast"}
        service.queue(request, "operator", uuid4().hex)
        one = service.work_once()["run_id"]
        service.approve(one, "Benchmark verified holdout evidence", "reviewer", uuid4().hex)
        service.deploy(
            "forecast", one, None, "Benchmark initial deployment", "operator", uuid4().hex
        )
        from datetime import date, timedelta

        payload = {
            "sku": "SKU-001",
            "location": "CHI",
            "start": str(date.fromisoformat(rows[days - 1]["day"]) + timedelta(days=1)),
            "horizon": 14,
            "promotion": False,
        }
        first = service.infer("forecast", payload, "operator", uuid4().hex)
        service.queue({**request, "ridge_alpha": 2}, "operator", uuid4().hex)
        two = service.work_once()["run_id"]
        service.approve(two, "Benchmark verified challenger evidence", "reviewer", uuid4().hex)
        service.deploy(
            "forecast", two, one, "Benchmark challenger deployment", "operator", uuid4().hex
        )
        second = service.infer("forecast", payload, "operator", uuid4().hex)
        service.deploy(
            "forecast",
            one,
            two,
            "Benchmark prior-version rollback",
            "operator",
            uuid4().hex,
            rollback=True,
        )
        restored = service.infer("forecast", payload, "operator", uuid4().hex)
        checks["rollback_exact_predictions"] = (
            first["results"] == restored["results"] and first["results"] != second["results"]
        )
        checks["rollback_exact_artifact"] = first["artifact_sha256"] == restored["artifact_sha256"]
        checks["dataset_traceability"] = first["dataset_fingerprint"] == ds["fingerprint"]
        drift_data = "".join(
            json.dumps(r) + "\n" for r in generate(43, days, series, True)
        ).encode()
        shifted = service.ingest(drift_data, "shifted.jsonl", "operator", uuid4().hex)
        monitoring = service.monitor("forecast", shifted["id"], "operator", uuid4().hex)
        checks["drift_alert"] = monitoring["alert"] and monitoring["features"]["demand"]["alert"]
        with TestClient(create_app(settings, boot=False)) as client:
            response = client.post(
                "/api/v1/predictions/forecast",
                json=payload,
                headers={
                    "Authorization": "Bearer " + settings.tokens["operator"],
                    "Idempotency-Key": uuid4().hex,
                },
            )
            checks["deployment_api_smoke"] = (
                response.status_code == 200
                and response.json()["run_id"] == one
                and len(response.json()["results"]) == 14
            )
        checks["rollback_audit"] = any(
            e["kind"] == "model_rolled_back" for e in service.store.rows("events")
        )
    result = {
        "schema_version": 1,
        "training_code_sha256": hashlib.sha256(
            (Path(__file__).parents[1] / "domain/models.py").read_bytes()
        ).hexdigest(),
        "measured_at": datetime.now(UTC).isoformat(),
        "hardware": hardware(),
        "dataset": {
            "rows": len(rows),
            "days": days,
            "series": series,
            "raw_sha256": hashlib.sha256(encoded).hexdigest(),
        },
        "timings": timings,
        "quality": quality,
        "artifact_hashes": artifacts,
        "checks": checks,
        "total_seconds": time.perf_counter() - start,
        "process_peak_rss_mib": peak_memory(),
        "scope": "Synthetic local single-process benchmark. RSS includes imports and the API smoke test; not an isolated model allocation. No Docker or live LLM benchmark.",
    }
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    with (out / "results.csv").open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            [
                "task",
                "rows",
                "repeats",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "quality_metric",
                "quality_value",
            ]
        )
        for task in timings:
            name = "wape" if task == "forecast" else "f1"
            t = timings[task]
            writer.writerow(
                [
                    task,
                    len(rows),
                    repeats,
                    t["median_seconds"],
                    t["min_seconds"],
                    t["max_seconds"],
                    name,
                    quality[task][name],
                ]
            )
    md = [
        "# Measured local benchmark",
        "",
        f"Measured: {result['measured_at']}",
        "",
        f"Hardware: {result['hardware']['cpu']} · {result['hardware']['os']} · Python {platform.python_version()} · NumPy {np.__version__}",
        "",
        f"Dataset: {len(rows):,} observations, {series} SKU/location series, {days} days. Seed 42. Local AI disabled.",
        "",
        "| Pipeline | Median training | Quality |",
        "|---|---:|---:|",
    ]
    md += [
        f"| Forecast | {timings['forecast']['median_seconds'] * 1000:.3f} ms | WAPE {quality['forecast']['wape']:.4%} (baseline {quality['forecast']['baseline_wape']:.4%}) |",
        f"| Anomaly | {timings['anomaly']['median_seconds'] * 1000:.3f} ms | F1 {quality['anomaly']['f1']:.4f} |",
    ]
    md += [
        "",
        f"{repeats} repeats per pipeline; complete harness {result['total_seconds']:.3f} s; process peak RSS {result['process_peak_rss_mib']:.1f} MiB."
        if result["process_peak_rss_mib"]
        else f"{repeats} repeats; memory unavailable on this platform.",
        "",
        "## Lifecycle assertions",
        "",
    ] + [
        f"- [{'x' if passed else ' '}] {name.replace('_', ' ')}" for name, passed in checks.items()
    ]
    md += [
        "",
        result["scope"],
        "",
        "Re-run with `python -m scml.evaluation.benchmark`. Performance varies with hardware and background load. Synthetic quality is not a production accuracy claim.",
        "",
    ]
    (out / "summary.md").write_text("\n".join(md))
    if not all(checks.values()):
        raise AssertionError("Benchmark assertions failed; inspect results.json")
    print(
        json.dumps(
            {
                "output": str(out),
                "checks_passed": sum(checks.values()),
                "checks_total": len(checks),
                "rows": len(rows),
                "seconds": result["total_seconds"],
            },
            indent=2,
        )
    )
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="output/benchmark")
    p.add_argument("--days", type=int, default=180)
    p.add_argument("--series", type=int, default=4)
    p.add_argument("--repeats", type=int, default=5)
    a = p.parse_args()
    if a.repeats < 2:
        p.error("--repeats must be at least 2")
    benchmark(a.output, a.days, a.series, a.repeats)


if __name__ == "__main__":
    main()
