import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from scml.data.generator import generate
from scml.data.store import Store
from scml.domain.errors import DomainError
from scml.services.lifecycle import Lifecycle

REASON = "Evidence verified for controlled deployment"
PAYLOAD = {
    "sku": "SKU-001",
    "location": "CHI",
    "start": "2025-06-30",
    "horizon": 14,
    "promotion": False,
}


def test_unapproved_deployment_blocked(service, trained):
    with pytest.raises(DomainError, match="approved"):
        service.deploy("forecast", trained["id"], None, REASON, "operator", uuid4().hex)
    assert service.active("forecast") is None


def test_self_approval_blocked(service, trained):
    with pytest.raises(DomainError, match="independent"):
        service.approve(trained["id"], REASON, "operator", uuid4().hex)


def test_atomic_deployment_and_rollback(service, dataset, deployed):
    original = service.infer("forecast", PAYLOAD, "operator", uuid4().hex)
    service.queue(
        {"dataset_id": dataset["id"], "task": "forecast", "ridge_alpha": 2},
        "operator",
        uuid4().hex,
    )
    job = service.work_once()
    candidate = job["run_id"]
    service.approve(candidate, REASON, "reviewer", uuid4().hex)
    service.deploy("forecast", candidate, deployed["id"], REASON, "operator", uuid4().hex)
    changed = service.infer("forecast", PAYLOAD, "operator", uuid4().hex)
    assert changed["results"] != original["results"]
    service.deploy(
        "forecast", deployed["id"], candidate, REASON, "operator", uuid4().hex, rollback=True
    )
    restored = service.infer("forecast", PAYLOAD, "operator", uuid4().hex)
    assert restored["results"] == original["results"]
    assert restored["artifact_sha256"] == original["artifact_sha256"]
    assert any(e["kind"] == "model_rolled_back" for e in service.store.rows("events"))


def test_concurrent_idempotency(service, dataset):
    req = {"dataset_id": dataset["id"], "task": "forecast"}
    key = uuid4().hex
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: service.queue(req, "operator", key), range(4)))
    assert len({r["id"] for r in results}) == 1
    assert len(service.store.rows("jobs")) == 1
    with pytest.raises(DomainError, match="different request"):
        service.queue({**req, "seed": 12}, "operator", key)


def test_stale_deploy_rejected(service, dataset, deployed):
    service.queue({"dataset_id": dataset["id"], "task": "forecast"}, "operator", uuid4().hex)
    job = service.work_once()
    service.approve(job["run_id"], REASON, "reviewer", uuid4().hex)
    with pytest.raises(DomainError, match="changed"):
        service.deploy("forecast", job["run_id"], None, REASON, "operator", uuid4().hex)
    assert service.active("forecast") == deployed["id"]


def test_artifact_integrity_fail_closed(service, deployed):
    with service.store.transaction() as db:
        run = service.require("runs", deployed["id"], db)
        run["artifact"]["seed"] = 12345
        service.store.put(db, "runs", run)
    with pytest.raises(DomainError, match="integrity"):
        service.infer("forecast", PAYLOAD, "operator", uuid4().hex)
    assert not service.store.rows("predictions")


def test_persistent_schedule_coalesces_and_never_promotes(service, dataset):
    item = service.schedule(
        {
            "dataset_id": dataset["id"],
            "task": "forecast",
            "interval_minutes": 5,
            "seed": 42,
            "enabled": True,
        },
        "operator",
        uuid4().hex,
    )

    def due():
        with service.store.transaction() as db:
            s = service.require("schedules", item["id"], db)
            s["next_run_at"] = "2020-01-01T00:00:00+00:00"
            service.store.put(db, "schedules", s)

    due()
    assert service.tick() == 1
    due()
    assert service.tick() == 0
    fresh = Lifecycle(Store(service.store.root))
    job = fresh.work_once()
    assert job["status"] == "succeeded"
    assert fresh.require("runs", job["run_id"])["stage"] == "candidate"
    assert fresh.active("forecast") is None


def test_expired_worker_lease_recovered(service, dataset):
    job = service.queue({"dataset_id": dataset["id"], "task": "forecast"}, "operator", uuid4().hex)
    with service.store.transaction() as db:
        job.update(status="running", attempts=1, lease_until="2020-01-01T00:00:00+00:00")
        service.store.put(db, "jobs", job)
    result = service.work_once()
    assert result["attempts"] == 2 and result["status"] == "succeeded"


def test_bad_dataset_blocks_training(service, encoded):
    bad = service.ingest(encoded + b"bad\n", "invalid.jsonl", "operator", uuid4().hex)
    with pytest.raises(DomainError, match="validation"):
        service.queue({"dataset_id": bad["id"], "task": "forecast"}, "operator", uuid4().hex)
    assert service.store.rows("jobs") == []


def test_shifted_drift_alert(service, deployed):
    data = "".join(json.dumps(r) + "\n" for r in generate(43, shift=True)).encode()
    ds = service.ingest(data, "drift.jsonl", "operator", uuid4().hex)
    monitor = service.monitor("forecast", ds["id"], "operator", uuid4().hex)
    assert monitor["alert"] and monitor["features"]["demand"]["alert"]
    # Demand is an observed target, not a forecast feature; a calendar model can stay stable.
    assert not monitor["features"]["prediction"]["alert"]
    assert monitor["run_id"] == deployed["id"]


def test_inference_retry_preserves_original_version(service, deployed):
    key = uuid4().hex
    first = service.infer("forecast", PAYLOAD, "operator", key)
    again = service.infer("forecast", PAYLOAD, "operator", key)
    assert first == again and len(service.store.rows("predictions")) == 1


def test_read_connection_cannot_mutate(service):
    import sqlite3

    with service.store.connect(True) as db:
        with pytest.raises(sqlite3.OperationalError):
            db.execute("DELETE FROM runs")
