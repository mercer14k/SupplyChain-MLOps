from uuid import uuid4

from tests.conftest import headers


def ingest(client, encoded):
    return client.post(
        "/api/v1/datasets?filename=demand.jsonl",
        content=encoded,
        headers={**headers(client), "Content-Type": "application/x-ndjson"},
    )


def test_api_primary_workflow(client, encoded):
    ds = ingest(client, encoded).json()
    response = client.post(
        "/api/v1/training",
        json={"dataset_id": ds["id"], "task": "forecast"},
        headers=headers(client),
    )
    assert response.status_code == 202
    done = client.app.state.service.work_once()
    run = done["run_id"]
    approve = client.post(
        f"/api/v1/runs/{run}/approve",
        json={"reason": "Validated holdout metrics and provenance"},
        headers=headers(client, "reviewer"),
    )
    assert approve.status_code == 200
    deploy = client.post(
        "/api/v1/deployments/forecast",
        json={
            "run_id": run,
            "reason": "Approved model smoke test deployment",
            "expected_current": None,
        },
        headers=headers(client),
    )
    assert deploy.status_code == 200
    prediction = client.post(
        "/api/v1/predictions/forecast",
        json={"sku": "SKU-001", "location": "CHI", "start": "2025-06-30", "horizon": 7},
        headers=headers(client),
    )
    assert prediction.status_code == 200 and len(prediction.json()["results"]) == 7
    assert prediction.json()["run_id"] == run and prediction.headers["x-trace-id"]
    assert client.get(f"/api/v1/runs/{run}/artifact").status_code == 200


def test_roles_and_auth(client, encoded):
    assert client.post("/api/v1/training", json={}).status_code in (401, 422)
    assert (
        client.post(
            "/api/v1/datasets?filename=d.jsonl",
            content=encoded,
            headers={**headers(client, "reviewer"), "Content-Type": "application/x-ndjson"},
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/session", headers=headers(client, "reviewer")).json()["role"]
        == "reviewer"
    )


def test_consistent_error(client):
    r = client.get("/api/v1/datasets/nonexistent")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
    assert r.json()["error"]["trace_id"] == r.headers["x-trace-id"]
    invalid = client.get("/api/v1/datasets?limit=1000")
    assert invalid.status_code == 422 and invalid.json()["error"]["details"]


def test_reject_origin_and_mime(client, encoded):
    h = headers(client)
    r = client.post(
        "/api/v1/datasets?filename=a.jsonl",
        content=encoded,
        headers={**h, "Origin": "https://malicious.test", "Content-Type": "application/x-ndjson"},
    )
    assert r.status_code == 403
    assert (
        client.post(
            "/api/v1/datasets?filename=a.jsonl",
            content=encoded,
            headers={**h, "Content-Type": "text/plain"},
        ).status_code
        == 415
    )


def test_health_readiness_pagination_openapi(client, encoded):
    ingest(client, encoded)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["status"] == "ready"
    page = client.get("/api/v1/datasets?limit=1&offset=0").json()
    assert page["total"] == 1 and page["limit"] == 1
    assert client.get("/api/v1/datasets?offset=1").json()["items"] == []
    schema = client.get("/openapi.json").json()
    assert "/api/v1/deployments/{task}/rollback" in schema["paths"]


def test_unknown_series_is_explicit_error(client, encoded):
    ds = ingest(client, encoded).json()
    s = client.app.state.service
    s.queue({"dataset_id": ds["id"], "task": "forecast"}, "operator", uuid4().hex)
    run = s.work_once()["run_id"]
    s.approve(run, "Evidence verified by independent reviewer", "reviewer", uuid4().hex)
    s.deploy("forecast", run, None, "Approved deployment for inference", "operator", uuid4().hex)
    response = client.post(
        "/api/v1/predictions/forecast",
        json={"sku": "unknown", "location": "CHI", "start": "2025-06-30"},
        headers=headers(client),
    )
    assert response.status_code == 422 and response.json()["error"]["code"] == "missing_evidence"


def test_malformed_import_remains_visible(client):
    r = ingest(client, b"{not json}\n")
    assert r.status_code == 201 and r.json()["validation"]["rejected"] == 1
    assert client.get("/api/v1/datasets").json()["total"] == 1


def test_disabled_ai_does_not_call_runtime(client, encoded):
    ds = ingest(client, encoded).json()
    s = client.app.state.service
    s.queue({"dataset_id": ds["id"], "task": "forecast"}, "operator", uuid4().hex)
    run = s.work_once()["run_id"]
    r = client.post(
        f"/api/v1/runs/{run}/explain",
        json={"model": "user-chosen-local-model"},
        headers=headers(client),
    )
    assert r.json()["status"] == "abstained"
    assert "disabled" in r.json()["reason"]


def test_chunked_body_is_bounded_before_parsing(client):
    from scml.services.ingestion import MAX_BYTES

    chunks = (b"x" * 1024 for _ in range(MAX_BYTES // 1024 + 1))
    result = client.post(
        "/api/v1/training",
        content=chunks,
        headers={**headers(client), "Content-Type": "application/json"},
    )
    assert result.status_code == 413 and result.json()["error"]["code"] == "file_too_large"


def test_operator_cannot_approve(client, encoded):
    ds = ingest(client, encoded).json()
    service = client.app.state.service
    service.queue({"dataset_id": ds["id"], "task": "forecast"}, "operator", uuid4().hex)
    run = service.work_once()["run_id"]
    result = client.post(
        f"/api/v1/runs/{run}/approve",
        json={"reason": "This actor must not bypass the reviewer role"},
        headers=headers(client),
    )
    assert result.status_code == 403
    assert service.require("runs", run)["stage"] == "candidate"
