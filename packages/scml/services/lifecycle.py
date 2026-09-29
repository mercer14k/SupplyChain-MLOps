"""Application services: atomic state transitions, immutable evidence, durable jobs."""

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from scml.data.store import encode
from scml.domain.errors import DomainError
from scml.domain.models import anomaly_score, artifact_hash, drift, forecast_value, train
from scml.domain.schemas import TrainRequest
from scml.observability.logging import log
from scml.services.ingestion import validate


def now():
    return datetime.now(UTC).isoformat()


def new_id(prefix):
    return prefix + "-" + uuid4().hex[:24]


def public_dataset(ds):
    return {k: v for k, v in ds.items() if k != "records"}


def public_run(run):
    return {k: v for k, v in run.items() if k not in ("artifact", "chart")}


class Lifecycle:
    def __init__(self, store):
        self.store = store

    def require(self, table, ident, db=None):
        item = self.store.get(table, ident, db)
        if item is None:
            raise DomainError(f"{table} evidence not found", "not_found", 404)
        return item

    def event(self, db, kind, actor, **payload):
        item = {"id": new_id("evt"), "created_at": now(), "kind": kind, "actor": actor, **payload}
        self.store.put(db, "events", item)
        return item

    def once(self, key, scope, body, action):
        digest = hashlib.sha256(encode({"scope": scope, "body": body}).encode()).hexdigest()
        with self.store.transaction() as db:
            previous = db.execute("SELECT * FROM idempotency WHERE key=?", (key,)).fetchone()
            if previous:
                if previous["fingerprint"] != digest:
                    raise DomainError(
                        "Idempotency key was already used for a different request",
                        "idempotency_conflict",
                    )
                return json.loads(previous["response"])
            result = action(db)
            db.execute("INSERT INTO idempotency VALUES (?,?,?)", (key, digest, encode(result)))
            return result

    def ingest(self, data, filename, actor, key):
        dataset = validate(data, filename)

        def action(db):
            old = self.store.get("datasets", dataset["id"], db)
            if old:
                return public_dataset(old)
            self.store.put(db, "datasets", dataset)
            self.event(
                db,
                "dataset_imported",
                actor,
                dataset_id=dataset["id"],
                fingerprint=dataset["fingerprint"],
                validation=dataset["validation"]["status"],
            )
            return public_dataset(dataset)

        return self.once(
            key, "ingest:" + actor, {"hash": dataset["raw_sha256"], "name": dataset["name"]}, action
        )

    def queue(self, request, actor, key):
        request = TrainRequest.model_validate(request).model_dump()
        return self.once(key, "train:" + actor, request, lambda db: self._queue(db, request, actor))

    def _queue(self, db, request, actor):
        dataset = self.require("datasets", request["dataset_id"], db)
        if dataset["validation"]["status"] != "valid":
            raise DomainError(
                "Training is blocked by dataset validation errors", "invalid_dataset", 422
            )
        job = {
            "id": new_id("job"),
            "created_at": now(),
            "status": "queued",
            "request": request,
            "actor": actor,
            "attempts": 0,
            "run_id": None,
            "error": None,
            "lease_until": None,
        }
        self.store.put(db, "jobs", job)
        self.event(
            db,
            "training_queued",
            actor,
            job_id=job["id"],
            dataset_id=dataset["id"],
            task=request["task"],
        )
        return job

    def work_once(self):
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT payload FROM jobs WHERE status IN ('queued','running') ORDER BY created_at"
            ).fetchall()
            job = next(
                (
                    j
                    for row in rows
                    if (j := json.loads(row["payload"]))["status"] == "queued"
                    or j["lease_until"] < now()
                ),
                None,
            )
            if not job:
                return None
            if job["attempts"] >= 3:
                job.update(status="failed", error="Worker retry limit exceeded", lease_until=None)
                self.store.put(db, "jobs", job)
                self.event(db, "training_failed", "worker", job_id=job["id"], error=job["error"])
                return job
            job.update(
                status="running",
                lease_until=(datetime.now(UTC) + timedelta(minutes=10)).isoformat(),
                attempts=job["attempts"] + 1,
            )
            lease = job["lease_until"]
            self.store.put(db, "jobs", job)
        start = time.perf_counter()
        req = job["request"]
        try:
            dataset = self.require("datasets", req["dataset_id"])
            artifact, metrics, gate, chart = train(
                dataset["records"], req["task"], req["seed"], req["ridge_alpha"]
            )
            code_hash = hashlib.sha256(
                (Path(__file__).parents[1] / "domain/models.py").read_bytes()
            ).hexdigest()
            artifact["training_code_sha256"] = code_hash
            artifact["dataset_fingerprint"] = dataset["fingerprint"]
            digest = artifact_hash(artifact)
            run = {
                "id": "run-" + hashlib.sha256(job["id"].encode()).hexdigest()[:24],
                "created_at": now(),
                "task": req["task"],
                "stage": "candidate",
                "dataset_id": dataset["id"],
                "dataset_fingerprint": dataset["fingerprint"],
                "artifact_sha256": digest,
                "code_sha256": code_hash,
                "parameters": req,
                "metrics": metrics,
                "gate": gate,
                "artifact": artifact,
                "chart": chart,
                "trained_by": job["actor"],
                "approved_by": None,
                "duration_seconds": time.perf_counter() - start,
                "job_id": job["id"],
            }
            with self.store.transaction() as db:
                current = self.require("jobs", job["id"], db)
                if current["status"] != "running" or current["lease_until"] != lease:
                    return current
                self.store.put(db, "runs", run)
                job.update(status="succeeded", run_id=run["id"], lease_until=None)
                self.store.put(db, "jobs", job)
                self.event(
                    db,
                    "training_completed",
                    "worker",
                    run_id=run["id"],
                    job_id=job["id"],
                    artifact_sha256=digest,
                    task=run["task"],
                )
            log(
                "training_completed",
                run_id=run["id"],
                dataset_id=dataset["id"],
                duration_seconds=run["duration_seconds"],
                seed=req["seed"],
            )
        except Exception as e:
            message = (
                e.message if isinstance(e, DomainError) else "Training failed; inspect server logs"
            )
            with self.store.transaction() as db:
                current = self.require("jobs", job["id"], db)
                if current["lease_until"] == lease:
                    job.update(status="failed", error=message, lease_until=None)
                    self.store.put(db, "jobs", job)
                    self.event(db, "training_failed", "worker", job_id=job["id"], error=message)
            log("training_failed", job_id=job["id"], error_type=type(e).__name__)
        return job

    def approve(self, run_id, reason, actor, key):
        def action(db):
            run = self.require("runs", run_id, db)
            if run["stage"] != "candidate":
                raise DomainError("Only candidate models can be approved")
            if not run["gate"]["passed"]:
                raise DomainError("Model failed the quality gate", "quality_gate_failed")
            if actor == run["trained_by"]:
                raise DomainError(
                    "Reviewer must be independent of the training actor",
                    "separation_of_duties",
                    403,
                )
            self.verify_artifact(run)
            run.update(
                stage="approved", approved_by=actor, approved_at=now(), approval_reason=reason
            )
            self.store.put(db, "runs", run)
            self.event(db, "model_approved", actor, run_id=run_id, reason=reason)
            return public_run(run)

        return self.once(key, "approve:" + actor, {"run_id": run_id, "reason": reason}, action)

    @staticmethod
    def verify_artifact(run):
        if artifact_hash(run["artifact"]) != run["artifact_sha256"]:
            raise DomainError("Model artifact integrity check failed", "artifact_integrity", 409)
        if run["artifact"].get("format") != 1:
            raise DomainError("Unsupported artifact format", "artifact_format", 409)

    def active(self, task, db=None):
        if db is None:
            with self.store.connect(True) as conn:
                return self.active(task, conn)
        row = db.execute("SELECT run_id FROM deployments WHERE task=?", (task,)).fetchone()
        return row["run_id"] if row else None

    def deploy(self, task, run_id, expected_current, reason, actor, key, rollback=False):
        def action(db):
            previous = self.active(task, db)
            if previous != expected_current:
                raise DomainError(
                    "Deployment changed. Refresh and review before retrying.", "stale_deployment"
                )
            if previous == run_id:
                raise DomainError("This model is already deployed")
            run = self.require("runs", run_id, db)
            if (
                run["task"] != task
                or run["stage"] not in ("approved", "archived")
                or not run["approved_by"]
            ):
                raise DomainError("Model must be approved for this task", "approval_required")
            self.verify_artifact(run)
            if rollback:
                history = [
                    json.loads(r["payload"])
                    for r in db.execute(
                        "SELECT payload FROM events WHERE kind IN ('model_deployed','model_rolled_back')"
                    )
                ]
                if not any(e.get("run_id") == run_id and e.get("task") == task for e in history):
                    raise DomainError(
                        "Rollback target has no deployment history", "invalid_rollback"
                    )
            if previous:
                old = self.require("runs", previous, db)
                old["stage"] = "archived"
                self.store.put(db, "runs", old)
            run["stage"] = "production"
            self.store.put(db, "runs", run)
            db.execute(
                "INSERT INTO deployments VALUES (?,?,?) ON CONFLICT(task) DO UPDATE SET run_id=excluded.run_id, updated_at=excluded.updated_at",
                (task, run_id, now()),
            )
            event = self.event(
                db,
                "model_rolled_back" if rollback else "model_deployed",
                actor,
                task=task,
                run_id=run_id,
                previous_run_id=previous,
                reason=reason,
            )
            return {
                "task": task,
                "run_id": run_id,
                "previous_run_id": previous,
                "event_id": event["id"],
            }

        return self.once(
            key,
            ("rollback:" if rollback else "deploy:") + actor,
            locals_body(task, run_id, expected_current, reason),
            action,
        )

    def deployed_run(self, task):
        ident = self.active(task)
        if not ident:
            raise DomainError("Approve and deploy a model before inference", "not_deployed", 409)
        run = self.require("runs", ident)
        self.verify_artifact(run)
        return run

    def infer(self, task, payload, actor, key):
        # Deployment ID is recorded once with this result; retry never reruns on a new model.
        def action(db):
            active = self.active(task, db)
            if not active:
                raise DomainError(
                    "Approve and deploy a model before inference", "not_deployed", 409
                )
            run = self.require("runs", active, db)
            self.verify_artifact(run)
            artifact = run["artifact"]
            if task == "forecast":
                start = datetime.fromisoformat(payload["start"]).date()
                if payload["start"] <= artifact["data_end"]:
                    raise DomainError(
                        "Forecast start must be after the dataset end", "historical_inference", 422
                    )
                if (start - datetime.fromisoformat(artifact["data_end"]).date()).days + payload[
                    "horizon"
                ] - 1 > 90:
                    raise DomainError(
                        "Forecast must stay within 90 days of training data",
                        "forecast_horizon",
                        422,
                    )
                result = []
                for i in range(payload["horizon"]):
                    row = {**payload, "day": str(start + timedelta(days=i))}
                    value = forecast_value(artifact, row)
                    q = artifact["interval_q90"]
                    result.append(
                        {
                            "day": row["day"],
                            "prediction": value,
                            "lower": max(0, value - q),
                            "upper": value + q,
                        }
                    )
            else:
                result = [
                    {
                        "id": r["id"],
                        "score": (score := anomaly_score(artifact, r)),
                        "is_anomaly": score > artifact["threshold"],
                    }
                    for r in payload["observations"]
                ]
            out = {
                "id": new_id("pred"),
                "created_at": now(),
                "task": task,
                "run_id": run["id"],
                "dataset_fingerprint": run["dataset_fingerprint"],
                "artifact_sha256": run["artifact_sha256"],
                "input_fingerprint": hashlib.sha256(encode(payload).encode()).hexdigest(),
                "results": result,
            }
            self.store.put(db, "predictions", out)
            self.event(
                db,
                "inference_recorded",
                actor,
                prediction_id=out["id"],
                run_id=run["id"],
                count=len(result),
            )
            return out

        return self.once(key, "infer:" + task + ":" + actor, payload, action)

    def monitor(self, task, dataset_id, actor, key):
        def action(db):
            active = self.active(task, db)
            if not active:
                raise DomainError("Deploy a model before monitoring", "not_deployed")
            run = self.require("runs", active, db)
            self.verify_artifact(run)
            dataset = self.require("datasets", dataset_id, db)
            if dataset["validation"]["status"] != "valid":
                raise DomainError("Monitoring requires a validated dataset", "invalid_dataset", 422)
            rows = dataset["records"]
            artifact = run["artifact"]
            predict = forecast_value if task == "forecast" else anomaly_score
            results = {
                f: drift(artifact["reference"][f], [r[f] for r in rows])
                for f in ["demand", "lead_time_days", "fulfillment_rate"]
            }
            results["prediction"] = drift(
                artifact["reference"]["prediction"], [predict(artifact, r) for r in rows]
            )
            item = {
                "id": new_id("mon"),
                "created_at": now(),
                "task": task,
                "run_id": run["id"],
                "dataset_id": dataset_id,
                "dataset_fingerprint": dataset["fingerprint"],
                "features": results,
                "alert": any(r["alert"] for r in results.values()),
                "policy": {"psi_threshold": 0.25, "mean_shift_std_threshold": 3, "minimum_n": 30},
            }
            self.store.put(db, "monitors", item)
            self.event(
                db,
                "drift_alert" if item["alert"] else "drift_checked",
                actor,
                monitor_id=item["id"],
                run_id=run["id"],
                dataset_id=dataset_id,
            )
            return item

        return self.once(key, "monitor:" + actor, {"task": task, "dataset_id": dataset_id}, action)

    def schedule(self, payload, actor, key):
        def action(db):
            ds = self.require("datasets", payload["dataset_id"], db)
            if ds["validation"]["status"] != "valid":
                raise DomainError("Schedules require a validated dataset", "invalid_dataset", 422)
            item = {
                "id": new_id("schedule"),
                "created_at": now(),
                **payload,
                "next_run_at": (
                    datetime.now(UTC) + timedelta(minutes=payload["interval_minutes"])
                ).isoformat(),
                "actor": actor,
                "last_job_id": None,
            }
            self.store.put(db, "schedules", item)
            self.event(db, "schedule_created", actor, schedule_id=item["id"])
            return item

        return self.once(key, "schedule:" + actor, payload, action)

    def set_schedule(self, ident, enabled, actor, key):
        def action(db):
            item = self.require("schedules", ident, db)
            item["enabled"] = enabled
            self.store.put(db, "schedules", item)
            self.event(db, "schedule_updated", actor, schedule_id=ident, enabled=enabled)
            return item

        return self.once(key, "schedule_toggle:" + actor, {"id": ident, "enabled": enabled}, action)

    def tick(self):
        count = 0
        with self.store.transaction() as db:
            for row in db.execute("SELECT payload FROM schedules").fetchall():
                item = json.loads(row["payload"])
                if not item["enabled"] or item["next_run_at"] > now():
                    continue
                # Only one unresolved job per schedule. Missed ticks coalesce on restart.
                last = (
                    self.store.get("jobs", item["last_job_id"], db) if item["last_job_id"] else None
                )
                if not last or last["status"] in ("succeeded", "failed"):
                    req = TrainRequest(
                        dataset_id=item["dataset_id"], task=item["task"], seed=item["seed"]
                    ).model_dump()
                    job = self._queue(db, req, "scheduler")
                    item["last_job_id"] = job["id"]
                    count += 1
                item["next_run_at"] = (
                    datetime.now(UTC) + timedelta(minutes=item["interval_minutes"])
                ).isoformat()
                self.store.put(db, "schedules", item)
        return count


def locals_body(task, run_id, expected_current, reason):
    return {"task": task, "run_id": run_id, "expected_current": expected_current, "reason": reason}
