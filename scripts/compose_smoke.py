"""Real container smoke check without third-party client dependencies."""

import argparse
import json
import subprocess
import time
import urllib.request
from uuid import uuid4


def request(path, body=None, token=None):
    headers = {}
    if token:
        headers = {"Authorization": "Bearer " + token, "Idempotency-Key": uuid4().hex}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        "http://127.0.0.1:8018" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-only", action="store_true")
    args = parser.parse_args()
    assert request("/ready")["status"] == "ready"
    with urllib.request.urlopen("http://127.0.0.1:5188", timeout=30) as response:
        assert response.status == 200
    if args.read_only:
        assert request("/api/v1/overview")["deployments"]["forecast"]
        print("Persistent deployment survived container restart")
        return
    raw = subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import json; print(open('/state/credentials.json').read())",
        ],
        text=True,
    )
    keys = json.loads(raw)
    for _ in range(60):
        runs = request("/api/v1/runs")["items"]
        if len(runs) >= 2:
            break
        time.sleep(1)
    assert len(runs) >= 2 and all(r["gate"]["passed"] for r in runs)
    forecast = next(r for r in runs if r["task"] == "forecast")
    request(
        "/api/v1/runs/" + forecast["id"] + "/approve",
        {"reason": "Compose smoke verified model evidence"},
        keys["reviewer"],
    )
    request(
        "/api/v1/deployments/forecast",
        {
            "run_id": forecast["id"],
            "expected_current": None,
            "reason": "Compose smoke approved deployment",
        },
        keys["operator"],
    )
    result = request(
        "/api/v1/predictions/forecast",
        {"sku": "SKU-001", "location": "CHI", "start": "2025-06-30", "horizon": 7},
        keys["operator"],
    )
    assert len(result["results"]) == 7 and result["run_id"] == forecast["id"]
    print("Compose health, training, approval, deployment and inference verified")


if __name__ == "__main__":
    main()
