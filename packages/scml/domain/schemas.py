from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")]
Task = Literal["forecast", "anomaly"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Observation(StrictModel):
    id: Identifier
    source_id: Identifier
    ingested_at: datetime
    validation_status: Literal["valid"] = "valid"
    lineage: dict[str, str] = Field(default_factory=dict, max_length=20)
    day: date
    sku: Identifier
    location: Identifier
    demand: float = Field(ge=0, le=1e7)
    stock_on_hand: float = Field(ge=0, le=1e9)
    lead_time_days: float = Field(ge=0, le=365)
    fulfillment_rate: float = Field(ge=0, le=1)
    promotion: bool = False
    stockout: bool = False
    is_anomaly: bool = False

    @model_validator(mode="after")
    def aware(self):
        if self.ingested_at.tzinfo is None:
            raise ValueError("ingested_at must be timezone aware")
        return self


class TrainRequest(StrictModel):
    dataset_id: Identifier
    task: Task
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    ridge_alpha: float = Field(default=1.0, ge=0.001, le=100)


class Decision(StrictModel):
    reason: str = Field(min_length=12, max_length=1000)


class DeployRequest(Decision):
    run_id: Identifier
    expected_current: str | None = None


class ForecastRequest(StrictModel):
    sku: Identifier
    location: Identifier
    start: date
    horizon: int = Field(default=14, ge=1, le=90)
    promotion: bool = False


class AnomalyRequest(StrictModel):
    observations: list[Observation] = Field(min_length=1, max_length=500)


class MonitorRequest(StrictModel):
    dataset_id: Identifier
    task: Task


class ScheduleRequest(StrictModel):
    dataset_id: Identifier
    task: Task
    interval_minutes: int = Field(ge=5, le=525600)
    seed: int = Field(default=42, ge=0)
    enabled: bool = True


class ExplainRequest(StrictModel):
    model: str = Field(min_length=1, max_length=200, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$")


class Narrative(StrictModel):
    summary: str = Field(min_length=1, max_length=1200)
    evidence_ids: list[str] = Field(min_length=1, max_length=20)
    recommended_action: Literal["review_data", "review_candidate", "collect_evidence", "observe"]


class Page(StrictModel):
    items: list[dict]
    total: int
    limit: int
    offset: int


class ErrorDetail(StrictModel):
    code: str
    message: str
    trace_id: str
    details: list[dict] = Field(default_factory=list)


class ErrorResponse(StrictModel):
    error: ErrorDetail


class ValidationReport(StrictModel):
    accepted: int
    rejected: int
    total: int
    status: Literal["valid", "rejected"]
    errors: list[dict]


class DatasetSummary(StrictModel):
    id: Identifier
    created_at: datetime
    name: str
    raw_sha256: str
    fingerprint: str
    validation: ValidationReport
    source_ids: dict[str, int]
    date_start: date | None
    date_end: date | None
    series_count: int


class QualityGate(StrictModel):
    passed: bool
    policy: str
    reason: str


class RunSummary(StrictModel):
    id: Identifier
    created_at: datetime
    task: Task
    stage: Literal["candidate", "approved", "production", "archived"]
    dataset_id: Identifier
    dataset_fingerprint: str
    artifact_sha256: str
    code_sha256: str
    parameters: TrainRequest
    metrics: dict[str, float | int | bool | None]
    gate: QualityGate
    trained_by: str
    approved_by: str | None
    approved_at: datetime | None = None
    approval_reason: str | None = None
    duration_seconds: float
    job_id: Identifier


class RunDetail(RunSummary):
    artifact: dict
    chart: list[dict]


class JobResponse(StrictModel):
    id: Identifier
    created_at: datetime
    status: Literal["queued", "running", "succeeded", "failed"]
    request: TrainRequest
    actor: str
    attempts: int
    run_id: str | None
    error: str | None
    lease_until: datetime | None


class DeploymentResponse(StrictModel):
    task: Task
    run_id: Identifier
    previous_run_id: str | None
    event_id: Identifier


class PredictionResponse(StrictModel):
    id: Identifier
    created_at: datetime
    task: Task
    run_id: Identifier
    dataset_fingerprint: str
    artifact_sha256: str
    input_fingerprint: str
    results: list[dict]


class MonitorResponse(StrictModel):
    id: Identifier
    created_at: datetime
    task: Task
    run_id: Identifier
    dataset_id: Identifier
    dataset_fingerprint: str
    features: dict[str, dict]
    alert: bool
    policy: dict


class ScheduleResponse(ScheduleRequest):
    id: Identifier
    created_at: datetime
    next_run_at: datetime
    actor: str
    last_job_id: str | None


class NarrativeResponse(StrictModel):
    status: Literal["explained", "abstained"]
    reason: str
    narrative: Narrative | None
    evidence: dict
    telemetry: dict
