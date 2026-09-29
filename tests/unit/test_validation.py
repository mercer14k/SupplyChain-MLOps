import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from scml.domain.errors import DomainError
from scml.domain.schemas import Observation
from scml.services.ingestion import MAX_BYTES, validate


def test_duplicate_records_reported(encoded):
    ds = validate(encoded + encoded.splitlines()[0] + b"\n", "test.jsonl")
    assert ds["validation"]["rejected"] == 1
    assert "Duplicate" in ds["validation"]["errors"][0]["reason"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("demand", -1),
        ("lead_time_days", float("nan")),
        ("fulfillment_rate", 1.1),
        ("ingested_at", "2025-01-01T00:00:00"),
        ("extra_field", "instruction"),
    ],
)
def test_schema_rejects_invalid(records, field, value):
    with pytest.raises(ValidationError):
        Observation.model_validate({**records[0], field: value})


def test_invalid_lines_not_silently_discarded(encoded):
    result = validate(encoded + b"{bad}\n\n", "test.jsonl")
    assert result["validation"]["rejected"] == 2 and result["validation"]["status"] == "rejected"
    assert all(e["raw_sha256"] for e in result["validation"]["errors"])


def test_canonical_fingerprint_order_independent(encoded):
    one = validate(encoded, "a.jsonl")
    two = validate(b"\n".join(encoded.splitlines()[::-1]) + b"\n", "a.jsonl")
    assert one["fingerprint"] == two["fingerprint"] and one["raw_sha256"] != two["raw_sha256"]


def test_sanitize_filename(encoded):
    assert validate(encoded, "../../secret.jsonl")["name"] == "secret.jsonl"


@pytest.mark.parametrize(
    "data,name,code",
    [
        (b"", "a.txt", "unsupported_type"),
        (b"\xff", "a.jsonl", "encoding"),
        (b" " * (MAX_BYTES + 1), "a.jsonl", "file_too_large"),
    ],
)
def test_upload_limits(data, name, code):
    with pytest.raises(DomainError) as e:
        validate(data, name)
    assert e.value.code == code


def test_schema_file_matches_model():
    assert (
        json.loads(Path("data/schemas/observation.schema.json").read_text())
        == Observation.model_json_schema()
    )


def test_committed_sample_provenance():
    ds = validate(Path("data/sample/consignai.jsonl").read_bytes(), "consignai.jsonl")
    assert ds["validation"]["status"] == "valid"
    assert all(r["lineage"].get("upstream_snapshot") for r in ds["records"])
    assert all(
        "fulfillment is a stock proxy" in r["lineage"]["measurement_note"] for r in ds["records"]
    )
