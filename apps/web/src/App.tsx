import { useEffect, useState, type FormEvent } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Bell,
  BookOpen,
  Boxes,
  CheckCircle2,
  ChevronDown,
  Database,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Timer,
  X,
} from "lucide-react";
import { dateTime, metric, mutation, short, useResource } from "./api";
import {
  Badge,
  Empty,
  JsonEvidence,
  Loading,
  Modal,
  Pagination,
  Panel,
} from "./components";
import {
  AboutView,
  AccessDialog,
  DatasetDetail,
  InferenceView,
  OverviewView,
  RunDetail,
  RunTable,
  TrainDialog,
  UploadDialog,
} from "./views";
import type {
  AuditEvent,
  Dataset,
  Job,
  Monitor,
  Overview,
  Page,
  Role,
  Run,
  Schedule,
  Task,
} from "./types";

const navigation = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "registry", label: "Model registry", icon: Boxes },
  { id: "datasets", label: "Dataset versions", icon: Database },
  { id: "inference", label: "Inference", icon: Server },
  { id: "monitoring", label: "Monitoring", icon: Activity },
  { id: "workflows", label: "Retraining", icon: GitBranch },
  { id: "activity", label: "Audit trail", icon: ShieldCheck },
  { id: "about", label: "Architecture", icon: BookOpen },
];
const subtitles: Record<string, string> = {
  overview: "Every model. Every decision. One traceable lifecycle.",
  registry:
    "Compare evidence, review candidates, and control what reaches production.",
  datasets: "Immutable source versions with visible validation and lineage.",
  inference: "Serve operational forecasts from an approved model version.",
  monitoring: "Measure how incoming data and model outputs change.",
  workflows: "Durable training jobs and scheduled candidate creation.",
  activity:
    "A persistent record of imports, training, approvals, deployments and rollbacks.",
  about: "Inspect the system, its provenance, and its limits.",
};

export default function App() {
  const [route, setRoute] = useState("overview"),
    [refresh, setRefresh] = useState(0),
    [offset, setOffset] = useState(0),
    [search, setSearch] = useState(""),
    [task, setTask] = useState(""),
    [token, setToken] = useState(""),
    [role, setRole] = useState<Role>("viewer"),
    [modal, setModal] = useState(""),
    [runId, setRunId] = useState(""),
    [dataset, setDataset] = useState<Dataset | null>(null),
    [notice, setNotice] = useState(""),
    [sideOpen, setSideOpen] = useState(false),
    [operationError, setOperationError] = useState("");
  const overview = useResource<Overview>("/overview", refresh);
  const runs = useResource<Page<Run>>(
    `/runs?limit=25&offset=${route === "registry" ? offset : 0}${task ? "&task=" + task : ""}`,
    refresh,
  );
  const datasets = useResource<Page<Dataset>>(
    `/datasets?limit=25&offset=${route === "datasets" ? offset : 0}&q=${encodeURIComponent(route === "datasets" ? search : "")}`,
    refresh,
  );
  const selectorDatasets = useResource<Page<Dataset>>(
    "/datasets?limit=100",
    refresh,
  );
  const monitors = useResource<Page<Monitor>>(
    `/monitors?limit=25&offset=${route === "monitoring" ? offset : 0}`,
    refresh,
  );
  const jobs = useResource<Page<Job>>("/jobs?limit=25", refresh);
  const schedules = useResource<Page<Schedule>>(
    `/schedules?limit=25&offset=${route === "workflows" ? offset : 0}`,
    refresh,
  );
  const events = useResource<Page<AuditEvent>>(
    `/events?limit=25&offset=${route === "activity" ? offset : 0}`,
    refresh,
  );
  useEffect(() => {
    const i = setInterval(() => {
      if (!document.hidden) setRefresh((v) => v + 1);
    }, 8000);
    return () => clearInterval(i);
  }, []);
  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(""), 7000);
    return () => clearTimeout(t);
  }, [notice]);
  const reload = () => setRefresh((v) => v + 1);
  function navigate(next: string) {
    setRoute(next);
    setOffset(0);
    setSearch("");
    setSideOpen(false);
    setOperationError("");
  }
  function authorized(action: string) {
    if (role === "operator") setModal(action);
    else setModal("access");
  }
  async function toggleSchedule(s: Schedule) {
    try {
      await mutation(
        `/schedules/${s.id}/enabled?enabled=${!s.enabled}`,
        {},
        token,
      );
      reload();
      setNotice(
        s.enabled
          ? "Retraining schedule paused"
          : "Retraining schedule enabled",
      );
    } catch (e) {
      setOperationError((e as Error).message);
    }
  }
  const openRun = (id: string) => {
    setRunId(id);
    setModal("run");
  };
  const current = navigation.find((n) => n.id === route)!;
  const pageError = (
    {
      registry: runs.error,
      datasets: datasets.error,
      monitoring: monitors.error,
      workflows: schedules.error || jobs.error,
      activity: events.error,
    } as Record<string, string>
  )[route];
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${sideOpen ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-mark">
            <Boxes size={23} />
          </span>
          <span>
            SupplyChain
            <span className="brand-bottom">
              MLOps <small>OPEN SOURCE</small>
            </span>
          </span>
        </a>
        <div className="workspace-label">
          <span className="workspace-icon">S</span>
          <span>
            Local workspace<small>Development environment</small>
          </span>
          <ChevronDown size={15} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {navigation.slice(0, 7).map((n) => (
            <button
              key={n.id}
              className={route === n.id ? "nav-item selected" : "nav-item"}
              aria-current={route === n.id ? "page" : undefined}
              onClick={() => navigate(n.id)}
            >
              <n.icon size={18} />
              {n.label}
              {n.id === "registry" && overview.data?.pending_approvals ? (
                <span className="nav-count">
                  {overview.data.pending_approvals}
                </span>
              ) : null}
            </button>
          ))}
        </nav>
        <div className="nav-label second">RESOURCES</div>
        <button
          className={route === "about" ? "nav-item selected" : "nav-item"}
          onClick={() => navigate("about")}
        >
          <BookOpen size={18} />
          Architecture
        </button>
        <a
          className="nav-item"
          href="http://localhost:8018/docs"
          target="_blank"
          rel="noreferrer"
        >
          <FlaskConical size={18} />
          API reference <ArrowRight size={13} />
        </a>
        <div className="sidebar-bottom">
          <div className="local-card">
            <div>
              <span className="status-dot" />
              LOCAL FIRST
            </div>
            <p>Your data stays here.</p>
            <span>
              AI{" "}
              {overview.data?.ai.enabled
                ? "enabled · your model"
                : "disabled · no model required"}
            </span>
          </div>
          <button className="access-button" onClick={() => setModal("access")}>
            <span className="avatar">
              {role === "viewer" ? "R" : role === "operator" ? "O" : "V"}
            </span>
            <span>
              {role === "viewer"
                ? "Read-only access"
                : role === "operator"
                  ? "Operator access"
                  : "Reviewer access"}
              <small>Manage workspace access</small>
            </span>
            <LockKeyhole size={15} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setSideOpen((v) => !v)}
            >
              <Menu size={20} />
            </button>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>{current.label}</strong>
          </div>
          <div className="top-actions">
            <Badge tone="neutral">
              <span className="status-dot" />
              Local environment
            </Badge>
            <button
              className="icon-button"
              aria-label="Open audit trail"
              onClick={() => navigate("activity")}
            >
              <Bell size={18} />
            </button>
            <span className="avatar small">SC</span>
          </div>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                SUPPLYCHAIN MLOPS <span>/</span> CONTROL ROOM
              </div>
              <h1>
                {route === "overview" ? "Model operations" : current.label}
              </h1>
              <p>{subtitles[route]}</p>
            </div>
            <div className="heading-actions">
              <button
                className="button secondary"
                onClick={reload}
                aria-label="Refresh data"
              >
                <RefreshCw size={16} />
                <span>Refresh</span>
              </button>
              {route === "datasets" ? (
                <button
                  className="button primary"
                  onClick={() => authorized("upload")}
                >
                  <Plus size={17} />
                  Import dataset
                </button>
              ) : (
                <button
                  className="button primary"
                  onClick={() => authorized("train")}
                >
                  <Plus size={17} />
                  New training run
                </button>
              )}
            </div>
          </div>
          {notice ? (
            <div className="toast" role="status">
              <CheckCircle2 size={19} />
              {notice}
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          ) : null}
          {overview.error ? (
            <div className="error" role="alert">
              Cannot reach the API. {overview.error}{" "}
              <button onClick={reload}>Retry</button>
            </div>
          ) : null}
          {pageError || operationError ? (
            <p className="error" role="alert">
              {pageError || operationError}
            </p>
          ) : null}
          {!overview.data && overview.loading ? <Loading /> : null}
          {route === "overview" && overview.data ? (
            <OverviewView
              overview={overview.data}
              onOpen={openRun}
              onNavigate={navigate}
              refresh={refresh}
            />
          ) : null}
          {route === "registry" ? (
            <Panel
              title="Version history"
              action={
                <div className="filters">
                  <SlidersHorizontal size={16} />
                  <select
                    aria-label="Filter pipeline"
                    value={task}
                    onChange={(e) => {
                      setTask(e.target.value);
                      setOffset(0);
                    }}
                  >
                    <option value="">All pipelines</option>
                    <option value="forecast">Forecast</option>
                    <option value="anomaly">Anomaly detection</option>
                  </select>
                </div>
              }
            >
              {runs.loading && !runs.data ? (
                <Loading />
              ) : (
                <RunTable runs={runs.data?.items ?? []} onOpen={openRun} />
              )}
              <Pagination
                total={runs.data?.total ?? 0}
                offset={offset}
                onChange={setOffset}
              />
            </Panel>
          ) : null}
          {route === "datasets" ? (
            <Panel
              title="Source datasets"
              action={
                <label className="search">
                  <Search size={16} />
                  <input
                    aria-label="Search datasets"
                    placeholder="Search datasets…"
                    value={search}
                    onChange={(e) => {
                      setSearch(e.target.value);
                      setOffset(0);
                    }}
                  />
                </label>
              }
            >
              {datasets.loading && !datasets.data ? (
                <Loading />
              ) : datasets.data?.items.length ? (
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Dataset</th>
                        <th>Validation</th>
                        <th>Records</th>
                        <th>Series</th>
                        <th>Observation window</th>
                        <th>Fingerprint</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {datasets.data.items.map((d) => (
                        <tr key={d.id}>
                          <td>
                            <button
                              className="model-name"
                              onClick={() => setDataset(d)}
                            >
                              <Database size={18} />
                              <span>
                                {d.name}
                                <small>{short(d.id)}</small>
                              </span>
                            </button>
                          </td>
                          <td>
                            <Badge
                              tone={
                                d.validation.status === "valid"
                                  ? "green"
                                  : "red"
                              }
                            >
                              {d.validation.status === "valid"
                                ? "Validated"
                                : `${d.validation.rejected} rejected`}
                            </Badge>
                          </td>
                          <td>{d.validation.accepted.toLocaleString()}</td>
                          <td>{d.series_count}</td>
                          <td className="muted">
                            {d.date_start} — {d.date_end}
                          </td>
                          <td className="mono muted">
                            {d.fingerprint.slice(0, 10)}
                          </td>
                          <td>
                            <a
                              className="icon-button"
                              aria-label={`Export ${d.name}`}
                              href={`/api/v1/datasets/${d.id}/export`}
                              download
                            >
                              <ArrowDownToLine size={17} />
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <Empty title="No datasets found">
                  Import a JSONL dataset or clear the search.
                </Empty>
              )}
              <Pagination
                total={datasets.data?.total ?? 0}
                offset={offset}
                onChange={setOffset}
              />
            </Panel>
          ) : null}
          {route === "inference" && overview.data ? (
            <InferenceView
              overview={overview.data}
              token={token}
              role={role}
              onChanged={reload}
            />
          ) : null}
          {route === "monitoring" ? (
            <>
              <Panel
                title="Distribution monitoring"
                action={
                  <button
                    className="button primary"
                    onClick={() => authorized("monitor")}
                  >
                    <Activity size={16} />
                    Evaluate a batch
                  </button>
                }
              >
                <p className="section-note">
                  PSI above 0.25 or a mean shift above 3 standard deviations
                  triggers an alert. These checks flag distribution changes, not
                  accuracy loss.
                </p>
                {!monitors.data?.items.length ? (
                  <Empty title="No monitoring evidence yet">
                    Deploy a model, then evaluate the seeded drift dataset to
                    inspect a real alert.
                  </Empty>
                ) : (
                  monitors.data.items.map((m) => (
                    <div key={m.id} className="monitor-block">
                      <div className="monitor-title">
                        <div>
                          <h3>
                            {m.task === "forecast" ? "Forecast" : "Anomaly"} ·{" "}
                            {short(m.run_id)}
                          </h3>
                          <small>
                            {dateTime(m.created_at)} · {short(m.dataset_id)}
                          </small>
                        </div>
                        <Badge tone={m.alert ? "red" : "green"}>
                          {m.alert ? "Drift detected" : "Within thresholds"}
                        </Badge>
                      </div>
                      <div className="drift-grid">
                        {Object.entries(m.features).map(([key, f]) => (
                          <div key={key} className="drift-feature">
                            <span>{key.replaceAll("_", " ")}</span>
                            <strong className={f.alert ? "warn" : ""}>
                              {metric(f.psi)}
                              <small> PSI</small>
                            </strong>
                            <div
                              className="histogram"
                              aria-label={`${key}: reference and current distribution`}
                            >
                              {f.reference_counts.map((v, i) => (
                                <div key={i}>
                                  <i
                                    style={{
                                      height: `${Math.max(2, (v / f.reference_n) * 100)}%`,
                                    }}
                                  />
                                  <b
                                    style={{
                                      height: `${Math.max(2, (f.current_counts[i] / f.current_n) * 100)}%`,
                                    }}
                                  />
                                </div>
                              ))}
                            </div>
                            <small>
                              Reference {f.reference_n} · Current {f.current_n}
                            </small>
                          </div>
                        ))}
                      </div>
                      <details>
                        <summary>Inspect drift evidence</summary>
                        <JsonEvidence value={m} />
                      </details>
                    </div>
                  ))
                )}
                <Pagination
                  total={monitors.data?.total ?? 0}
                  offset={offset}
                  onChange={setOffset}
                />
              </Panel>
            </>
          ) : null}
          {route === "workflows" ? (
            <>
              <Panel
                title="Retraining schedules"
                action={
                  <button
                    className="button primary"
                    onClick={() => authorized("schedule")}
                  >
                    <Timer size={16} />
                    New schedule
                  </button>
                }
              >
                <p className="section-note">
                  Schedules create candidates from a pinned dataset version.
                  Quality checks and human approval still apply.
                </p>
                {schedules.data?.items.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Pipeline</th>
                          <th>Dataset version</th>
                          <th>Frequency</th>
                          <th>Next run</th>
                          <th>State</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {schedules.data.items.map((s) => (
                          <tr key={s.id}>
                            <td>{s.task}</td>
                            <td className="mono">{short(s.dataset_id)}</td>
                            <td>Every {s.interval_minutes} minutes</td>
                            <td>{dateTime(s.next_run_at)}</td>
                            <td>
                              <Badge tone={s.enabled ? "green" : "neutral"}>
                                {s.enabled ? "Enabled" : "Paused"}
                              </Badge>
                            </td>
                            <td>
                              <button
                                className="button secondary"
                                disabled={role !== "operator"}
                                onClick={() => toggleSchedule(s)}
                              >
                                {s.enabled ? "Pause" : "Enable"}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty title="No schedules configured">
                    Choose a validated dataset and a retraining interval.
                  </Empty>
                )}
                <Pagination
                  total={schedules.data?.total ?? 0}
                  offset={offset}
                  onChange={setOffset}
                />
              </Panel>
              <Panel title="Recent training jobs" eyebrow="DURABLE WORKER">
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Job</th>
                        <th>Pipeline</th>
                        <th>Status</th>
                        <th>Attempts</th>
                        <th>Created</th>
                        <th>Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {jobs.data?.items.map((j) => (
                        <tr key={j.id}>
                          <td className="mono">{short(j.id)}</td>
                          <td>{j.request.task}</td>
                          <td>
                            <Badge
                              tone={
                                j.status === "succeeded"
                                  ? "green"
                                  : j.status === "failed"
                                    ? "red"
                                    : "amber"
                              }
                            >
                              {j.status}
                            </Badge>
                          </td>
                          <td>{j.attempts}</td>
                          <td>{dateTime(j.created_at)}</td>
                          <td>
                            {j.run_id ? (
                              <button
                                className="text-link"
                                onClick={() => openRun(j.run_id!)}
                              >
                                Inspect model <ArrowRight size={14} />
                              </button>
                            ) : (
                              (j.error ?? "Waiting for worker")
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="section-note">
                  Showing the latest {jobs.data?.items.length ?? 0} jobs of{" "}
                  {jobs.data?.total ?? 0}. Full paginated history is available
                  in the API.
                </p>
              </Panel>
            </>
          ) : null}
          {route === "activity" ? (
            <Panel
              title="Lifecycle events"
              action={<Badge>{events.data?.total ?? 0} events</Badge>}
            >
              {events.data?.items.length ? (
                <div className="audit-list">
                  {events.data.items.map((e) => (
                    <div className="audit-item" key={e.id}>
                      <span className="audit-icon">
                        <ShieldCheck size={17} />
                      </span>
                      <div>
                        <strong>{e.kind.replaceAll("_", " ")}</strong>
                        <span>
                          {e.actor} ·{" "}
                          <code>{short(e.run_id ?? e.dataset_id ?? e.id)}</code>
                        </span>
                        {e.reason ? <p>{e.reason}</p> : null}
                      </div>
                      <time>{dateTime(e.created_at)}</time>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty title="No lifecycle events yet" />
              )}
              <Pagination
                total={events.data?.total ?? 0}
                offset={offset}
                onChange={setOffset}
              />
            </Panel>
          ) : null}
          {route === "about" ? <AboutView /> : null}
          <footer>
            <span>
              SupplyChain MLOps <span className="muted">/</span> v0.1.0
            </span>
            <span>Open source. Observable by design.</span>
          </footer>
        </main>
      </div>
      {modal === "access" ? (
        <AccessDialog
          close={() => setModal("")}
          onConnect={(t, r) => {
            setToken(t);
            setRole(r);
            setNotice(`Connected with ${r} access`);
          }}
        />
      ) : null}
      {modal === "train" ? (
        <TrainDialog
          token={token}
          datasets={selectorDatasets.data?.items ?? []}
          close={() => setModal("")}
          onDone={() => {
            reload();
            setNotice("Training queued. Follow its progress in Retraining.");
          }}
        />
      ) : null}
      {modal === "upload" ? (
        <UploadDialog
          token={token}
          close={() => setModal("")}
          onDone={() => {
            reload();
            setNotice("Dataset imported. Review its validation report.");
          }}
        />
      ) : null}
      {modal === "run" && overview.data ? (
        <RunDetail
          id={runId}
          close={() => setModal("")}
          token={token}
          role={role}
          overview={overview.data}
          onChanged={reload}
          onNotice={setNotice}
        />
      ) : null}
      {dataset ? (
        <DatasetDetail dataset={dataset} close={() => setDataset(null)} />
      ) : null}
      {modal === "monitor" || modal === "schedule" ? (
        <OperationDialog
          kind={modal}
          token={token}
          datasets={selectorDatasets.data?.items ?? []}
          close={() => setModal("")}
          onDone={() => {
            reload();
            setNotice(
              modal === "monitor"
                ? "Distribution check recorded"
                : "Retraining schedule created",
            );
          }}
        />
      ) : null}
    </div>
  );
}

function OperationDialog({
  kind,
  token,
  datasets,
  close,
  onDone,
}: {
  kind: "monitor" | "schedule";
  token: string;
  datasets: Dataset[];
  close: () => void;
  onDone: () => void;
}) {
  const [task, setTask] = useState<Task>("forecast"),
    [dataset, setDataset] = useState(
      datasets.find(
        (d) => d.name === (kind === "monitor" ? "drift.jsonl" : "demand.jsonl"),
      )?.id ?? "",
    ),
    [interval, setIntervalMinutes] = useState(1440),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await mutation(
        kind === "monitor" ? "/monitors" : "/schedules",
        kind === "monitor"
          ? { task, dataset_id: dataset }
          : {
              task,
              dataset_id: dataset,
              interval_minutes: interval,
              seed: 42,
              enabled: true,
            },
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
    <Modal
      title={
        kind === "monitor"
          ? "Evaluate distribution drift"
          : "Schedule controlled retraining"
      }
      onClose={close}
    >
      <form onSubmit={submit}>
        <label>
          Pipeline
          <select
            value={task}
            onChange={(e) => setTask(e.target.value as Task)}
          >
            <option value="forecast">Demand forecast</option>
            <option value="anomaly">Anomaly detection</option>
          </select>
        </label>
        <label>
          Validated dataset
          <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
            {datasets
              .filter((d) => d.validation.status === "valid")
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
          </select>
        </label>
        {kind === "schedule" ? (
          <label>
            Repeat every (minutes)
            <input
              type="number"
              min="5"
              max="525600"
              required
              value={interval}
              onChange={(e) => setIntervalMinutes(Number(e.target.value))}
            />
          </label>
        ) : (
          <p className="subtle">
            The seeded drift dataset changes demand, lead time, and fulfillment.
            Predictions are compared with the deployed model’s training
            reference.
          </p>
        )}
        {error ? (
          <p className="error" role="alert">
            {error}
          </p>
        ) : null}
        <button className="button primary full" disabled={busy || !dataset}>
          {busy
            ? "Working…"
            : kind === "monitor"
              ? "Run drift evaluation"
              : "Create schedule"}
        </button>
      </form>
    </Modal>
  );
}
