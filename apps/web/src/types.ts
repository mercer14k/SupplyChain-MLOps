export type Task = "forecast" | "anomaly";
export type Role = "viewer" | "operator" | "reviewer";
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
export interface Run {
  id: string;
  created_at: string;
  task: Task;
  stage: string;
  dataset_id: string;
  dataset_fingerprint: string;
  artifact_sha256: string;
  code_sha256: string;
  parameters: { seed: number; ridge_alpha: number };
  metrics: Record<string, number | boolean | null>;
  gate: { passed: boolean; policy: string; reason: string };
  duration_seconds: number;
  approved_by: string | null;
  trained_by: string;
  artifact?: {
    data_end: string;
    train_end: string;
    calibration_end: string;
    series: Record<string, unknown>;
    threshold?: number;
  };
  chart?: Point[];
}
export interface Point {
  day: string;
  sku: string;
  location: string;
  actual?: number;
  prediction?: number;
  score?: number;
  truth?: boolean;
  flag?: boolean;
  lower?: number;
  upper?: number;
}
export interface Dataset {
  id: string;
  name: string;
  created_at: string;
  fingerprint: string;
  raw_sha256: string;
  series_count: number;
  date_start: string;
  date_end: string;
  source_ids: Record<string, number>;
  validation: {
    accepted: number;
    rejected: number;
    total: number;
    status: string;
    errors: {
      line: number;
      reason: string;
      raw_preview: string;
      raw_sha256: string;
    }[];
  };
}
export interface FeatureDrift {
  psi: number;
  mean_shift_std: number;
  alert: boolean;
  reference_n: number;
  current_n: number;
  current_mean: number;
  reference_mean: number;
  reference_counts: number[];
  current_counts: number[];
  edges: number[];
}
export interface Monitor {
  id: string;
  created_at: string;
  task: Task;
  run_id: string;
  dataset_id: string;
  features: Record<string, FeatureDrift>;
  alert: boolean;
}
export interface Job {
  id: string;
  created_at: string;
  status: string;
  request: { task: Task; dataset_id: string };
  attempts: number;
  run_id: string | null;
  error: string | null;
}
export interface Schedule {
  id: string;
  created_at: string;
  task: Task;
  dataset_id: string;
  interval_minutes: number;
  next_run_at: string;
  enabled: boolean;
  last_job_id: string | null;
}
export interface AuditEvent {
  id: string;
  created_at: string;
  kind: string;
  actor: string;
  reason?: string;
  run_id?: string;
  dataset_id?: string;
}
export interface Overview {
  datasets: number;
  accepted_records: number;
  rejected_records: number;
  runs: number;
  pending_approvals: number;
  deployments: Record<Task, string | null>;
  latest_monitor: Monitor | null;
  worker_online: boolean;
  active_jobs: number;
  ai: { enabled: boolean; runtime: string; model: string | null };
  latest_runs: Run[];
}
export interface Prediction {
  id: string;
  run_id: string;
  artifact_sha256: string;
  dataset_fingerprint: string;
  results: {
    day?: string;
    prediction?: number;
    lower?: number;
    upper?: number;
    score?: number;
    is_anomaly?: boolean;
    id?: string;
  }[];
}
export interface Explanation {
  status: string;
  reason: string;
  narrative: {
    summary: string;
    evidence_ids: string[];
    recommended_action: string;
  } | null;
  evidence: Record<string, unknown>;
  telemetry: Record<string, unknown>;
}
