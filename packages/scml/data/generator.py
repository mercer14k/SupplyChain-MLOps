"""Deterministic demand fixture; labels are for evaluation, never model features."""

import argparse
import gzip
import hashlib
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


def generate(seed=42, days=180, series=4, shift=False):
    if days < 90 or series < 1 or series > 200:
        raise ValueError("days >= 90 and 1 <= series <= 200 required")
    rng = random.Random(seed)
    source = f"standalone-demand-v1-s{seed}-d{days}-n{series}-shift{int(shift)}"
    for k in range(series):
        for t in range(days):
            day = date(2025, 1, 1) + timedelta(days=t)
            promo = t % 30 in (10, 11, 12)
            mean = 40 + k * 14 + t * 0.08 + [8, 10, 6, 3, 0, -12, -16][day.weekday()] + 20 * promo
            anomaly = t in (int(days * 0.78) + k, days - 9 - k)
            demand = max(0, round(mean + rng.gauss(0, 3)))
            lead = max(1, 7 + k + rng.gauss(0, 0.7))
            fill = min(1, max(0, 0.975 + rng.gauss(0, 0.008)))
            if anomaly:
                lead += 16
                fill -= 0.35
            if shift:
                demand = round(demand * 1.7)
                lead += 6
                fill -= 0.10
            yield {
                "id": f"{source}:{k}:{t}",
                "source_id": source,
                "ingested_at": "2025-12-31T00:00:00+00:00",
                "validation_status": "valid",
                "lineage": {"generator": "standalone-demand-v1", "seed": str(seed)},
                "day": str(day),
                "sku": f"SKU-{k + 1:03}",
                "location": ["CHI", "DFW", "ATL", "PHX"][k % 4],
                "demand": demand,
                "stock_on_hand": demand * 12,
                "lead_time_days": round(lead, 3),
                "fulfillment_rate": round(fill, 4),
                "promotion": promo,
                "stockout": False,
                "is_anomaly": anomaly,
            }


def consignai(path):
    """Adapt actual ConsignAI movements and snapshots; preserve upstream record IDs.

    Zero usage on a day is explicit, not a dropped record. Fulfillment and lead time
    are not observed by ConsignAI: material lead time and a documented stock proxy
    are used. These records are not passed off as labeled fulfillment measurements.
    """
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as f:
        raw = [json.loads(line) for line in f if line.strip()]
    materials = {r["id"]: r for r in raw if r["record_type"] == "material"}
    usage = defaultdict(float)
    movement_ids = defaultdict(list)
    for r in raw:
        if r["record_type"] == "movement" and r["kind"] == "usage":
            key = (r["day"], r["sku"], r["from_location"])
            usage[key] += r["quantity"]
            movement_ids[key].append(r["id"])
    for r in raw:
        if r["record_type"] != "snapshot" or not r["location_id"].startswith(("c", "f")):
            continue
        key = (r["day"], r["sku"], r["location_id"])
        material = materials[r["sku"]]
        yield {
            "id": "consignai:" + hashlib.sha256(r["id"].encode()).hexdigest()[:24],
            "source_id": r["source_id"],
            "ingested_at": r["ingested_at"],
            "validation_status": "valid",
            "lineage": {
                "adapter": "consignai-v1",
                "upstream_snapshot": r["id"],
                "usage_record_ids": ",".join(movement_ids[key]),
                "measurement_note": "material lead time; fulfillment is a stock proxy; anomaly labels unavailable",
            },
            "day": r["day"],
            "sku": r["sku"],
            "location": r["location_id"],
            "demand": usage[key],
            "stock_on_hand": r["on_hand"],
            "lead_time_days": material["lead_time_days"],
            "fulfillment_rate": 1 if r["on_hand"] else 0,
            "promotion": False,
            "stockout": r["on_hand"] == 0,
            "is_anomaly": False,
        }


def write_jsonl(path, records):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "".join(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in records)
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="data/sample/demand.jsonl")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--days", type=int, default=180)
    p.add_argument("--series", type=int, default=4)
    p.add_argument("--shift", action="store_true")
    p.add_argument("--consignai")
    a = p.parse_args()
    write_jsonl(
        a.output,
        consignai(a.consignai) if a.consignai else generate(a.seed, a.days, a.series, a.shift),
    )


if __name__ == "__main__":
    main()
