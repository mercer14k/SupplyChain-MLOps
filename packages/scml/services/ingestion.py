import hashlib
from collections import Counter
from datetime import UTC, datetime
from pathlib import PurePath

from pydantic import ValidationError

from scml.data.store import encode
from scml.domain.errors import DomainError
from scml.domain.schemas import Observation

MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100000


def validate(data: bytes, filename: str):
    if len(data) > MAX_BYTES:
        raise DomainError("Dataset exceeds 16 MiB", "file_too_large", 413)
    if not filename.endswith(".jsonl"):
        raise DomainError("Only UTF-8 .jsonl datasets are supported", "unsupported_type", 415)
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeDecodeError as e:
        raise DomainError("Dataset must be UTF-8", "encoding", 422) from e
    if len(lines) > MAX_ROWS:
        raise DomainError("Dataset exceeds 100,000 lines", "file_too_large", 413)
    valid, errors, seen, natural = [], [], set(), set()
    for number, line in enumerate(lines, 1):
        try:
            if not line.strip():
                raise ValueError("Blank record")
            record = Observation.model_validate_json(line).model_dump(mode="json")
            key = (record["day"], record["sku"], record["location"])
            if record["id"] in seen:
                raise ValueError("Duplicate stable record ID")
            if key in natural:
                raise ValueError("Duplicate day/SKU/location observation")
            seen.add(record["id"])
            natural.add(key)
            valid.append(record)
        except (ValidationError, ValueError) as e:
            message = (
                "; ".join(
                    f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                    for err in e.errors(include_input=False, include_url=False)
                )
                if isinstance(e, ValidationError)
                else str(e)
            )
            errors.append(
                {
                    "line": number,
                    "status": "invalid",
                    "reason": message[:1000],
                    "raw_sha256": hashlib.sha256(line.encode()).hexdigest(),
                    "raw_preview": line[:300],
                }
            )
    canonical = sorted(valid, key=lambda r: r["id"])
    fingerprint = hashlib.sha256(encode(canonical).encode()).hexdigest()
    raw_sha = hashlib.sha256(data).hexdigest()
    now = datetime.now(UTC).isoformat()
    return {
        "id": "ds-" + raw_sha[:24],
        "created_at": now,
        "name": PurePath(filename.replace("\\", "/")).name[:120],
        "raw_sha256": raw_sha,
        "fingerprint": fingerprint,
        "records": canonical,
        "validation": {
            "accepted": len(valid),
            "rejected": len(errors),
            "total": len(lines),
            "errors": errors,
            "status": "rejected" if errors or not valid else "valid",
        },
        "source_ids": dict(Counter(r["source_id"] for r in valid)),
        "date_start": min((r["day"] for r in valid), default=None),
        "date_end": max((r["day"] for r in valid), default=None),
        "series_count": len({(r["sku"], r["location"]) for r in valid}),
    }
