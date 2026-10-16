export type Sli = {
  requests: number;
  errors: number;
  rps: number;
  availability: number | null;
  error_rate: number | null;
  p50: number | null;
  p95: number | null;
  p99: number | null;
  latency_sli: number | null;
  budget_remaining: number | null;
  burn_rate: number | null;
};
export type Summary = Sli & {
  history: (Sli & { at: number })[];
  endpoints: (Sli & { route: string })[];
  histogram: { le: number; count: number }[];
  window_seconds: number;
  version: string;
  uptime: number;
  database_ready: boolean;
  active_incidents: number;
  faults_enabled: boolean;
  fault: string;
  status: string;
  source: string;
  sample_retention_truncated: boolean;
};
export type Incident = {
  id: string;
  kind: string;
  severity: string;
  start: number;
  end: number | null;
  evidence: {
    metric: number;
    requests: number;
    window_seconds: number;
    endpoints: string[];
  };
  timeline: { at: number; action: string; detail: string }[];
  notes: string;
  status: string;
};
export type Experiment = {
  scenario: string;
  split: string;
  kind: string;
  expected_impact: boolean;
  detected: boolean;
  requests: number;
  success_rate: number;
  p95_seconds: number;
  detection_seconds: number | null;
  recovery_seconds: number | null;
  [key: string]: unknown;
};
export const pct = (n: number | null | undefined) =>
  n == null ? "—" : `${(n * 100).toFixed(2)}%`;
export const ms = (n: number | null | undefined) =>
  n == null ? "—" : `${(n * 1000).toFixed(1)} ms`;
export const time = (n: number) =>
  new Date(n * 1000).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
