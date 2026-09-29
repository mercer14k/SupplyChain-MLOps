import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  Check,
  Copy,
  Download,
  GitBranch,
  ShieldCheck,
  Upload,
  Activity,
} from "lucide-react";
import { api, dateTime, metric, mutation, short, useResource } from "./api";
import {
  Badge,
  Chart,
  Empty,
  JsonEvidence,
  Loading,
  Modal,
  Panel,
  TextLink,
} from "./components";
import type {
  Dataset,
  Explanation,
  Overview,
  Page,
  Point,
  Prediction,
  Role,
  Run,
  Task,
} from "./types";

export function RunTable({
  runs,
  onOpen,
}: {
  runs: Run[];
  onOpen: (id: string) => void;
}) {
  return runs.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Model / version</th>
            <th>Stage</th>
            <th>Quality</th>
            <th>Evaluation</th>
            <th>Dataset fingerprint</th>
            <th>Trained</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td>
                <button className="model-name" onClick={() => onOpen(r.id)}>
                  <span className={`model-icon ${r.task}`}>
                    <GitBranch size={17} />
                  </span>
                  <span>
                    {r.task === "forecast"
                      ? "Demand forecast"
                      : "Lead-time anomalies"}
                    <small>{short(r.id)}</small>
                  </span>
                </button>
              </td>
              <td>
                <Badge
                  tone={
                    r.stage === "production"
                      ? "green"
                      : r.stage === "candidate"
                        ? "amber"
                        : "neutral"
                  }
                >
                  {r.stage}
                </Badge>
              </td>
              <td>
                <span className={r.gate.passed ? "good" : "warn"}>
                  {r.gate.passed ? "Passed" : "Blocked"}
                </span>
              </td>
              <td className="mono">
                {r.task === "forecast"
                  ? `${metric(r.metrics.wape, true)} WAPE`
                  : `${metric(r.metrics.f1)} F1`}
              </td>
              <td className="mono muted">
                {r.dataset_fingerprint.slice(0, 10)}
              </td>
              <td className="muted">{dateTime(r.created_at)}</td>
              <td>
                <button
                  className="icon-button"
                  aria-label={`Review ${r.id}`}
                  onClick={() => onOpen(r.id)}
                >
                  <ArrowRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty title="No model versions yet">
      Load a validated dataset and start a training run.
    </Empty>
  );
}

export function OverviewView({
  overview,
  onOpen,
  onNavigate,
  refresh,
}: {
  overview: Overview;
  onOpen: (id: string) => void;
  onNavigate: (s: string) => void;
  refresh: number;
}) {
  const preferred = overview.latest_runs.find((r) => r.task === "forecast");
  const chart = useResource<Run>(
    preferred ? `/runs/${preferred.id}` : "/runs?limit=1",
    refresh,
  );
  const [series, setSeries] = useState("");
  const options = Object.keys(chart.data?.artifact?.series ?? {});
  const selected = options.includes(series) ? series : options[0];
  const points = (chart.data?.chart ?? []).filter(
    (p) => `${p.sku}|${p.location}` === selected,
  );
  const active = Object.values(overview.deployments).filter(Boolean).length;
  return (
    <>
      <div className="metrics-grid">
        <div className="metric-card">
          <span>
            Models in production <Activity size={17} />
          </span>
          <strong>{active.toString().padStart(2, "0")}</strong>
          <small>
            {active
              ? "Approved and serving locally"
              : "Deploy your first approved model"}
          </small>
        </div>
        <div className="metric-card">
          <span>
            Tracked experiments <GitBranch size={17} />
          </span>
          <strong>{overview.runs.toString().padStart(2, "0")}</strong>
          <small>{overview.active_jobs} training jobs in progress</small>
        </div>
        <div className="metric-card">
          <span>
            Awaiting review <ShieldCheck size={17} />
          </span>
          <strong className="lime">
            {overview.pending_approvals.toString().padStart(2, "0")}
          </strong>
          <small>Human approval before promotion</small>
        </div>
        <div className="metric-card">
          <span>
            Data health <span className="tiny-tag">VALIDATED</span>
          </span>
          <strong>
            {overview.accepted_records.toLocaleString()}
            <span className="metric-unit">records</span>
          </strong>
          <small>
            {overview.rejected_records} invalid records surfaced ·{" "}
            {overview.datasets} datasets
          </small>
        </div>
      </div>
      <div className="overview-grid">
        <Panel
          title="Demand forecast performance"
          eyebrow="MODEL EVIDENCE"
          action={
            <select
              aria-label="Chart series"
              value={selected ?? ""}
              onChange={(e) => setSeries(e.target.value)}
            >
              {options.map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          }
        >
          <div className="chart-kpis">
            <div>
              <small>Pooled holdout WAPE</small>
              <strong>{metric(chart.data?.metrics?.wape, true)}</strong>
            </div>
            <div>
              <small>Weekly baseline</small>
              <strong className="muted">
                {metric(chart.data?.metrics?.baseline_wape, true)}
              </strong>
            </div>
            <div>
              <small>Interval coverage</small>
              <strong className="muted">
                {metric(chart.data?.metrics?.interval_coverage, true)}
              </strong>
            </div>
          </div>
          {chart.error ? (
            <p role="alert" className="error">
              {chart.error}
            </p>
          ) : chart.loading && !chart.data ? (
            <Loading />
          ) : (
            <Chart points={points} />
          )}
          <div className="panel-foot">
            <span>
              Metrics pooled across series · chart shows selected series
            </span>
            {preferred ? (
              <TextLink onClick={() => onOpen(preferred.id)}>
                Inspect evidence
              </TextLink>
            ) : null}
          </div>
        </Panel>
        <Panel
          title="Promotion queue"
          eyebrow="HUMAN IN THE LOOP"
          action={
            <Badge tone="amber">{overview.pending_approvals} pending</Badge>
          }
          className="queue-panel"
        >
          <p className="subtle">
            Every deployment starts with evidence and an independent review.
          </p>
          {overview.latest_runs
            .filter((r) => r.stage === "candidate")
            .slice(0, 3)
            .map((r) => (
              <button
                className="queue-item"
                key={r.id}
                onClick={() => onOpen(r.id)}
              >
                <div className="queue-title">
                  <span>
                    {r.task === "forecast"
                      ? "Demand forecast"
                      : "Lead-time anomalies"}
                  </span>
                  <ArrowRight size={17} />
                </div>
                <div className="queue-detail">
                  <code>{short(r.id)}</code>
                  <Badge tone={r.gate.passed ? "green" : "amber"}>
                    {r.gate.passed ? "Gate passed" : "Gate failed"}
                  </Badge>
                </div>
              </button>
            ))}
          {overview.pending_approvals === 0 ? (
            <Empty title="Queue is clear">New training runs arrive here.</Empty>
          ) : null}
          <div className="guardrail">
            <ShieldCheck size={19} />
            <div>
              <strong>Promotion is protected</strong>
              <span>Reviewers approve. Operators deploy.</span>
            </div>
          </div>
        </Panel>
      </div>
      <Panel
        title="Recent model versions"
        action={
          <TextLink onClick={() => onNavigate("registry")}>
            View registry
          </TextLink>
        }
      >
        <RunTable runs={overview.latest_runs.slice(0, 5)} onOpen={onOpen} />
      </Panel>
      <div className="bottom-strip">
        <span>
          <span
            className={`status-dot ${overview.worker_online ? "" : "offline"}`}
          />
          {overview.worker_online
            ? "Retraining worker online"
            : "Retraining worker offline"}
        </span>
        <span>
          Versioned data → reproducible training → controlled promotion
        </span>
        <button onClick={() => onNavigate("about")}>
          Explore the architecture <ArrowRight size={14} />
        </button>
      </div>
    </>
  );
}

export function RunDetail({
  id,
  close,
  token,
  role,
  overview,
  onChanged,
  onNotice,
}: {
  id: string;
  close: () => void;
  token: string;
  role: Role;
  overview: Overview;
  onChanged: () => void;
  onNotice: (s: string) => void;
}) {
  const [revision, setRevision] = useState(0),
    [reason, setReason] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [model, setModel] = useState(""),
    [explanation, setExplanation] = useState<Explanation | null>(null);
  const {
    data: run,
    loading,
    error: loadError,
  } = useResource<Run>(`/runs/${id}`, revision);
  async function action(kind: "approve" | "deploy" | "rollback") {
    if (!run) return;
    setBusy(true);
    setError("");
    try {
      const path =
        kind === "approve"
          ? `/runs/${id}/approve`
          : `/deployments/${run.task}${kind === "rollback" ? "/rollback" : ""}`;
      await mutation(
        path,
        kind === "approve"
          ? { reason }
          : {
              reason,
              run_id: id,
              expected_current: overview.deployments[run.task],
            },
        token,
      );
      onNotice(
        kind === "approve"
          ? "Model approved. An operator can now deploy it."
          : kind === "rollback"
            ? "Prior model restored. Audit event recorded."
            : "Model deployed. Inference now uses this version.",
      );
      setRevision((v) => v + 1);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function narrate() {
    setBusy(true);
    try {
      setExplanation(
        await mutation<Explanation>(`/runs/${id}/explain`, { model }, token),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const series = run?.chart?.[0];
  return (
    <Modal title="Model evidence & promotion" onClose={close} wide>
      {loading && !run ? (
        <Loading />
      ) : loadError ? (
        <p className="error">{loadError}</p>
      ) : run ? (
        <>
          <div className="detail-title">
            <div>
              <h3>
                {run.task === "forecast"
                  ? "Demand forecast"
                  : "Lead-time anomaly detector"}
              </h3>
              <code>{run.id}</code>
            </div>
            <Badge tone={run.stage === "production" ? "green" : "amber"}>
              {run.stage}
            </Badge>
          </div>
          <div className="detail-grid">
            <div>
              <small>DATASET FINGERPRINT</small>
              <code>{run.dataset_fingerprint}</code>
            </div>
            <div>
              <small>ARTIFACT SHA-256</small>
              <code>{run.artifact_sha256}</code>
            </div>
          </div>
          <div className={`gate ${run.gate.passed ? "passed" : "failed"}`}>
            <ShieldCheck size={19} />
            <span>{run.gate.reason}</span>
          </div>
          <Chart
            anomaly={run.task === "anomaly"}
            points={(run.chart ?? []).filter(
              (p) => p.sku === series?.sku && p.location === series?.location,
            )}
          />
          <div className="evidence-metrics">
            {Object.entries(run.metrics).map(([k, v]) => (
              <div key={k}>
                <small>{k.replaceAll("_", " ")}</small>
                <strong>
                  {typeof v === "boolean" ? String(v) : metric(v)}
                </strong>
              </div>
            ))}
          </div>
          <details>
            <summary>Training configuration & lineage</summary>
            <JsonEvidence
              value={{
                parameters: run.parameters,
                trained_by: run.trained_by,
                approved_by: run.approved_by,
                code_sha256: run.code_sha256,
                fit_end: run.artifact?.train_end,
                calibration_end: run.artifact?.calibration_end,
                data_end: run.artifact?.data_end,
                policy: run.gate.policy,
              }}
            />
          </details>
          <div className="action-area">
            <label>
              Decision reason
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                minLength={12}
                placeholder="Document why this model is safe to approve, deploy or restore."
              />
            </label>
            <div className="action-row">
              <a
                className="button secondary"
                href={`/api/v1/runs/${id}/artifact`}
                download
              >
                <Download size={16} />
                Export artifact
              </a>
              {run.stage === "candidate" ? (
                <button
                  className="button primary"
                  disabled={
                    busy ||
                    role !== "reviewer" ||
                    !run.gate.passed ||
                    reason.length < 12
                  }
                  onClick={() => action("approve")}
                >
                  <Check size={16} />
                  Approve candidate
                </button>
              ) : null}
              {run.stage === "approved" ? (
                <button
                  className="button primary"
                  disabled={busy || role !== "operator" || reason.length < 12}
                  onClick={() => action("deploy")}
                >
                  Deploy model <ArrowRight size={16} />
                </button>
              ) : null}
              {run.stage === "archived" ? (
                <button
                  className="button secondary"
                  disabled={busy || role !== "operator" || reason.length < 12}
                  onClick={() => action("rollback")}
                >
                  Roll back to this version
                </button>
              ) : null}
            </div>
            <p className="subtle">
              Current access: {role}. Approval requires a reviewer; deployment
              requires an operator.
            </p>
          </div>
          <details>
            <summary>
              Optional local AI explanation ·{" "}
              {overview.ai.enabled ? "enabled" : "disabled"}
            </summary>
            <p className="subtle">
              Choose any installed model supported by your configured local
              runtime. Narratives cannot change model state.
            </p>
            <label>
              Installed model name
              <input
                value={model}
                onChange={(e) => setModel(e.target.value)}
                placeholder="Your local model name"
              />
            </label>
            <button
              className="button secondary"
              disabled={
                !overview.ai.enabled || !model || role === "viewer" || busy
              }
              onClick={narrate}
            >
              Generate evidence summary
            </button>
            {explanation ? (
              <div className="narrative">
                <Badge>AI-generated narrative</Badge>
                <p>{explanation.narrative?.summary ?? explanation.reason}</p>
                <p className="mono">
                  {explanation.narrative?.evidence_ids.join(", ")}
                </p>
                <details>
                  <summary>Evidence and observable telemetry</summary>
                  <JsonEvidence value={explanation} />
                </details>
              </div>
            ) : null}
          </details>
          {error ? (
            <p role="alert" className="error">
              {error}
            </p>
          ) : null}
        </>
      ) : null}
    </Modal>
  );
}

export function TrainDialog({
  datasets,
  token,
  close,
  onDone,
}: {
  datasets: Dataset[];
  token: string;
  close: () => void;
  onDone: () => void;
}) {
  const [dataset, setDataset] = useState(
      datasets.find((d) => d.name === "demand.jsonl")?.id ??
        datasets.find((d) => d.validation.status === "valid")?.id ??
        "",
    ),
    [task, setTask] = useState<Task>("forecast"),
    [seed, setSeed] = useState(42),
    [alpha, setAlpha] = useState(1),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await mutation(
        "/training",
        { dataset_id: dataset, task, seed, ridge_alpha: alpha },
        token,
      );
      onDone();
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Start a training run" onClose={close}>
      <p className="subtle">
        Training produces a candidate, a reproducible artifact, and holdout
        evidence. Promotion requires review.
      </p>
      <form onSubmit={submit}>
        <label>
          Dataset
          <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
            {datasets
              .filter((d) => d.validation.status === "valid")
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} · {d.validation.accepted} records
                </option>
              ))}
          </select>
        </label>
        <label>
          Pipeline
          <select
            value={task}
            onChange={(e) => setTask(e.target.value as Task)}
          >
            <option value="forecast">Demand forecast · seasonal ridge</option>
            <option value="anomaly">
              Lead-time anomaly · robust deviation
            </option>
          </select>
        </label>
        <div className="form-grid">
          <label>
            Random seed
            <input
              type="number"
              min="0"
              max="2147483647"
              required
              value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
            />
          </label>
          <label>
            Ridge alpha
            <input
              type="number"
              min="0.001"
              max="100"
              step="0.001"
              required
              value={alpha}
              onChange={(e) => setAlpha(Number(e.target.value))}
            />
          </label>
        </div>
        {error ? (
          <p role="alert" className="error">
            {error}
          </p>
        ) : null}
        <button className="button primary full" disabled={busy || !dataset}>
          {busy ? "Queuing…" : "Queue training run"}
          <ArrowRight size={16} />
        </button>
      </form>
    </Modal>
  );
}

export function AccessDialog({
  close,
  onConnect,
}: {
  close: () => void;
  onConnect: (token: string, role: Role) => void;
}) {
  const [token, setToken] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await api<{ role: Role }>("/session", {
        headers: { Authorization: `Bearer ${token}` },
      });
      onConnect(token, result.role);
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Workspace access" onClose={close}>
      <p className="subtle">
        Read-only access is available now. Use your local operator or reviewer
        key to make changes. Keys stay in memory for this session.
      </p>
      <div className="code-command">
        <code>docker compose exec api scml keys</code>
        <button
          className="icon-button"
          aria-label="Copy credentials command"
          onClick={() =>
            navigator.clipboard.writeText("docker compose exec api scml keys")
          }
        >
          <Copy size={16} />
        </button>
      </div>
      <p className="subtle">
        Native development: run <code>scml keys</code> in the repository.
      </p>
      <form onSubmit={submit}>
        <label>
          Workspace key
          <input
            autoComplete="off"
            type="password"
            required
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Paste a local role key"
          />
        </label>
        {error ? (
          <p role="alert" className="error">
            {error}
          </p>
        ) : null}
        <button className="button primary full" disabled={busy}>
          Connect workspace <ArrowRight size={16} />
        </button>
      </form>
    </Modal>
  );
}

export function DatasetDetail({
  dataset,
  close,
}: {
  dataset: Dataset;
  close: () => void;
}) {
  const { data, loading, error } = useResource<Page<Record<string, unknown>>>(
    `/datasets/${dataset.id}/records?limit=5`,
    0,
  );
  return (
    <Modal title={dataset.name} onClose={close} wide>
      <div className="detail-grid">
        <div>
          <small>CANONICAL FINGERPRINT</small>
          <code>{dataset.fingerprint}</code>
        </div>
        <div>
          <small>RAW FILE SHA-256</small>
          <code>{dataset.raw_sha256}</code>
        </div>
      </div>
      <div className="gate">
        <ShieldCheck size={19} />
        {dataset.validation.accepted} valid records ·{" "}
        {dataset.validation.rejected} rejected records
      </div>
      <p>
        Invalid datasets remain visible and cannot enter training. Correct the
        source and upload a new version.
      </p>
      {dataset.validation.errors.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Line</th>
                <th>Validation failure</th>
                <th>Raw evidence</th>
              </tr>
            </thead>
            <tbody>
              {dataset.validation.errors.map((e) => (
                <tr key={e.line}>
                  <td>{e.line}</td>
                  <td>{e.reason}</td>
                  <td>
                    <code>{e.raw_preview}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <details open>
        <summary>Source lineage</summary>
        <JsonEvidence value={dataset.source_ids} />
      </details>
      <h3>Raw validated observations · first five</h3>
      {loading ? (
        <Loading />
      ) : error ? (
        <p className="error">{error}</p>
      ) : (
        <JsonEvidence value={data?.items} />
      )}
      <a
        className="button secondary"
        href={`/api/v1/datasets/${dataset.id}/export`}
        download
      >
        <Download size={16} />
        Export validated records
      </a>
    </Modal>
  );
}

export function UploadDialog({
  token,
  close,
  onDone,
}: {
  token: string;
  close: () => void;
  onDone: () => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    if (file.size > 16 * 1024 * 1024) {
      setError("Maximum file size is 16 MiB");
      return;
    }
    setBusy(true);
    try {
      await api("/datasets?filename=" + encodeURIComponent(file.name), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/x-ndjson",
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: file,
      });
      onDone();
      close();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Import a dataset version" onClose={close}>
      <p className="subtle">
        Upload canonical UTF-8 JSONL, up to 16 MiB. Every row is validated;
        rejected rows remain in the validation report.
      </p>
      <form onSubmit={submit}>
        <label className="upload-zone">
          <Upload size={28} />
          Select a JSONL file
          <input
            type="file"
            accept=".jsonl"
            required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </label>
        {error ? (
          <p role="alert" className="error">
            {error}
          </p>
        ) : null}
        <button className="button primary full" disabled={busy || !file}>
          Validate & import
        </button>
      </form>
    </Modal>
  );
}

export function InferenceView({
  overview,
  token,
  role,
  onChanged,
}: {
  overview: Overview;
  token: string;
  role: Role;
  onChanged: () => void;
}) {
  const id = overview.deployments.forecast;
  const { data: run } = useResource<Run>(
    id ? `/runs/${id}` : "/runs?limit=1",
    0,
  );
  const options = Object.keys(run?.artifact?.series ?? {});
  const [series, setSeries] = useState(""),
    [horizon, setHorizon] = useState(14),
    [promotion, setPromotion] = useState(false),
    [prediction, setPrediction] = useState<Prediction | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const selected = options.includes(series) ? series : options[0];
  const start = run?.artifact?.data_end
    ? new Date(new Date(run.artifact.data_end).getTime() + 86400000)
        .toISOString()
        .slice(0, 10)
    : "";
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const [sku, location] = selected.split("|");
      setPrediction(
        await mutation<Prediction>(
          "/predictions/forecast",
          { sku, location, start, horizon, promotion },
          token,
        ),
      );
      setError("");
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Panel title="Production inference" eyebrow="EXPLICIT MODEL OUTPUT">
      {!id ? (
        <Empty title="No forecast model deployed">
          Approve a candidate, then deploy it from the model registry.
        </Empty>
      ) : (
        <>
          <p className="subtle">
            Serving <code>{short(id)}</code>. Each request records the model
            version, dataset fingerprint, and input fingerprint.
          </p>
          <form className="inline-form" onSubmit={submit}>
            <label>
              SKU / location
              <select
                value={selected ?? ""}
                onChange={(e) => setSeries(e.target.value)}
              >
                {options.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </label>
            <label>
              Horizon (days)
              <input
                type="number"
                min="1"
                max="90"
                value={horizon}
                onChange={(e) => setHorizon(Number(e.target.value))}
              />
            </label>
            <label>
              Start date
              <input value={start} readOnly />
            </label>
            <label className="check-label">
              <input
                type="checkbox"
                checked={promotion}
                onChange={(e) => setPromotion(e.target.checked)}
              />
              Promotion planned
            </label>
            <button
              className="button primary"
              disabled={role !== "operator" || busy || !selected}
            >
              Run forecast <ArrowRight size={16} />
            </button>
          </form>
          {error ? (
            <p role="alert" className="error">
              {error}
            </p>
          ) : null}
          {prediction ? (
            <>
              <div className="gate">
                <Check size={17} />
                Prediction recorded · {short(prediction.id)}
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Predicted units</th>
                      <th>Lower interval</th>
                      <th>Upper interval</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prediction.results.map((r) => (
                      <tr key={r.day}>
                        <td>{r.day}</td>
                        <td>{r.prediction?.toFixed(1)}</td>
                        <td>{r.lower?.toFixed(1)}</td>
                        <td>{r.upper?.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <details>
                <summary>Prediction lineage</summary>
                <JsonEvidence
                  value={{
                    run_id: prediction.run_id,
                    artifact_sha256: prediction.artifact_sha256,
                    dataset_fingerprint: prediction.dataset_fingerprint,
                  }}
                />
              </details>
            </>
          ) : (
            <Empty title="Ready for a forecast">
              Predictions come from the deployed statistical model. No LLM is
              involved.
            </Empty>
          )}
        </>
      )}
    </Panel>
  );
}

export function AboutView() {
  return (
    <div className="about-grid">
      <Panel title="From experiment to operation" eyebrow="ARCHITECTURE">
        <p>
          A local-first MLOps reference platform for supply-chain engineers. The
          same deterministic core powers training, inference, and evaluation.
        </p>
        <div className="pipeline">
          {[
            "Versioned data",
            "Training worker",
            "Quality policy",
            "Reviewer approval",
            "Production model",
            "Drift monitor",
          ].map((x, i) => (
            <div key={x}>
              <span>{String(i + 1).padStart(2, "0")}</span>
              <strong>{x}</strong>
              <ArrowRight size={17} />
            </div>
          ))}
        </div>
        <h3>Real evidence, explicit boundaries</h3>
        <p>
          Demand forecasts use weekly seasonality, trend and planned promotion
          features. Stockout days are censored. Robust anomaly models flag
          unusual lead times and fulfillment rates without using ground-truth
          labels as inputs.
        </p>
        <p>
          Models are stored as inspectable JSON, with SHA-256 integrity checks.
          Dataset versions, parameters, quality results, approvals and rollback
          events persist in a SQLite WAL registry.
        </p>
      </Panel>
      <Panel title="Built to run on your machine">
        <div className="about-facts">
          <div>
            <strong>Python + NumPy</strong>
            <span>Deterministic pipelines and statistical models</span>
          </div>
          <div>
            <strong>FastAPI + SQLite</strong>
            <span>Typed contracts and atomic lifecycle changes</span>
          </div>
          <div>
            <strong>React + Vite</strong>
            <span>Evidence-backed operations workspace</span>
          </div>
          <div>
            <strong>Local AI · optional</strong>
            <span>
              Ollama, llama.cpp or vLLM adapters. Bring your own installed
              model. Disabled by default.
            </span>
          </div>
          <div>
            <strong>Apache-2.0</strong>
            <span>Open-source software. No paid API in the core path.</span>
          </div>
        </div>
        <h3>Dataset provenance</h3>
        <p>
          Includes the actual ConsignAI synthetic sample and this project’s
          standalone seeded demand generator. DemandSense has not been built; no
          DemandSense integration is claimed.
        </p>
        <h3>Scope</h3>
        <p>
          This is a single-node reference implementation. It is not a
          multi-tenant hosted service, a high-availability registry, or a
          calibrated inventory decision system. Synthetic holdout metrics are
          not production accuracy claims.
        </p>
      </Panel>
    </div>
  );
}

export function seriesPoints(points: Point[], key: string) {
  return points.filter((p) => `${p.sku}|${p.location}` === key);
}
