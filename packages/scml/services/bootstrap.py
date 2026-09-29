import os
from pathlib import Path

from scml.data.generator import consignai, generate, write_jsonl
from scml.services.lifecycle import Lifecycle


def bootstrap(service: Lifecycle, samples="data/sample"):
    if os.getenv("SCML_DEMO", "true").lower() != "true":
        return
    paths = [
        ("demand.jsonl", lambda: generate()),
        ("drift.jsonl", lambda: generate(43, shift=True)),
    ]
    for name, gen in paths:
        path = Path(samples) / name
        data = (
            path.read_bytes()
            if path.exists()
            else "".join(__import__("json").dumps(r) + "\n" for r in gen()).encode()
        )
        ds = service.ingest(data, name, "bootstrap", "bootstrap:" + name)
        if name == "demand.jsonl":
            for task in ("forecast", "anomaly"):
                service.queue(
                    {"dataset_id": ds["id"], "task": task}, "bootstrap", "bootstrap:" + task
                )
    path = Path(samples) / "consignai.jsonl"
    if path.exists():
        service.ingest(path.read_bytes(), path.name, "bootstrap", "bootstrap:consignai")
    path = Path(samples) / "invalid.jsonl"
    if path.exists():
        service.ingest(path.read_bytes(), path.name, "bootstrap", "bootstrap:invalid")


def generate_samples():
    write_jsonl("data/sample/demand.jsonl", generate())
    write_jsonl("data/sample/drift.jsonl", generate(43, shift=True))
    path = Path("data/upstream/consignai-mini.jsonl.gz")
    if path.exists():
        write_jsonl("data/sample/consignai.jsonl", consignai(path))
    Path("data/sample/ground-truth.json").write_text(
        __import__("json").dumps(
            {
                "seed": 42,
                "generator": "standalone-demand-v1",
                "anomaly_record_ids": [r["id"] for r in generate() if r["is_anomaly"]],
                "drift": {
                    "seed": 43,
                    "demand_multiplier": 1.7,
                    "lead_time_add_days": 6,
                    "fulfillment_add": -0.10,
                },
            },
            indent=2,
        )
        + "\n"
    )
    valid = next(generate())
    import json

    Path("data/sample/invalid.jsonl").write_text(
        json.dumps(valid) + "\n" + json.dumps({**valid, "demand": -5}) + "\n{bad json}\n"
    )
