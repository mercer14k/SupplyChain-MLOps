import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from scml.data.generator import generate
from scml.data.store import Store
from scml.services.config import Settings
from scml.services.lifecycle import Lifecycle

from apps.api.main import create_app


@pytest.fixture
def records():
    return list(generate())


@pytest.fixture
def encoded(records):
    return "".join(json.dumps(r) + "\n" for r in records).encode()


@pytest.fixture
def service(tmp_path):
    return Lifecycle(Store(tmp_path / "state"))


@pytest.fixture
def dataset(service, encoded):
    return service.ingest(encoded, "demand.jsonl", "operator", uuid4().hex)


@pytest.fixture
def trained(service, dataset):
    job = service.queue({"dataset_id": dataset["id"], "task": "forecast"}, "operator", uuid4().hex)
    result = service.work_once()
    assert result["id"] == job["id"] and result["status"] == "succeeded"
    return service.require("runs", result["run_id"])


@pytest.fixture
def deployed(service, trained):
    service.approve(
        trained["id"], "Chronological holdout and provenance verified", "reviewer", uuid4().hex
    )
    service.deploy(
        "forecast", trained["id"], None, "Approved baseline deployment", "operator", uuid4().hex
    )
    return trained


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCML_LLM_ENABLED", "false")
    settings = Settings(tmp_path / "api")
    with TestClient(create_app(settings, boot=False)) as client:
        yield client


def headers(client, role="operator", key=None):
    return {
        "Authorization": "Bearer " + client.app.state.settings.tokens[role],
        "Idempotency-Key": key or uuid4().hex,
    }
