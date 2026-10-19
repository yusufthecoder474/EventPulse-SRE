import { useCallback, useEffect, useState } from "react";
import WirelessLab from "./WirelessLab";
import {
  Activity,
  LayoutDashboard,
  Radio,
  Siren,
  Target,
  FlaskConical,
  ChartNoAxesCombined,
  ChevronRight,
  ArrowUpRight,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Database,
  Zap,
  Clock3,
  Check,
  Download,
  Terminal,
  Menu,
  X,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
} from "recharts";
import {
  type Summary,
  type Incident,
  type Experiment,
  pct,
  ms,
  time,
} from "./types";
const pages = [
  "Operations overview",
  "Service monitoring",
  "Incident center",
  "SLO dashboard",
  "Fault injection lab",
  "Experiment results",
  "WirelessLab",
];
const icons = [
  LayoutDashboard,
  Radio,
  Siren,
  Target,
  FlaskConical,
  ChartNoAxesCombined,
  Radio,
];
async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`/api${path}`, options);
  if (!r.ok) {
    const data = await r.json().catch(() => ({ error: r.statusText }));
    throw new Error(data.error || `HTTP ${r.status}`);
  }
  return r.json();
}
type ExperimentResults = {
  runs: Experiment[];
  summary: Record<string, unknown>;
  source: string;
  configuration_comparison?: {
    configuration: string;
    mode: string;
    precision: number | null;
    recall: number | null;
    false_alerts: number;
  }[];
};
function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="empty">
      <Radio size={24} />
      <p>{children}</p>
    </div>
  );
}
function Panel({
  title,
  sub,
  children,
  tag,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
  tag?: string;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {sub && <p>{sub}</p>}
        </div>
        {tag && <span className="pill neutral">{tag}</span>}
      </div>
      {children}
    </section>
  );
}
export default function App() {
  const [page, setPage] = useState(() =>
      new URLSearchParams(window.location.search).get("lab") === "wireless"
        ? 6
        : 0,
    ),
    [summary, setSummary] = useState<Summary | null>(null),
    [incidents, setIncidents] = useState<Incident[]>([]),
    [experiments, setExperiments] = useState<ExperimentResults | null>(null),
    [error, setError] = useState(""),
    [updated, setUpdated] = useState<Date | null>(null),
    [busy, setBusy] = useState(false),
    [menu, setMenu] = useState(false),
    [token, setToken] = useState(""),
    [delay, setDelay] = useState(750),
    [feedback, setFeedback] = useState(""),
    [note, setNote] = useState("");
  const refresh = useCallback(async () => {
    try {
      const [s, i, e] = await Promise.all([
        api<Summary>("/operations/summary"),
        api<Incident[]>("/operations/incidents"),
        api<ExperimentResults>("/operations/experiments"),
      ]);
      setSummary(s);
      setIncidents(i);
      setExperiments(e);
      setError("");
      setUpdated(new Date());
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 3000);
    return () => clearInterval(id);
  }, [refresh]);
  async function fault(kind: string) {
    setBusy(true);
    setFeedback("");
    try {
      await api("/operations/faults", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Lab-Token": token },
        body: JSON.stringify({ kind, delay_ms: delay, duration_seconds: 30 }),
      });
      setFeedback(
        kind === "none"
          ? "Fault cleared. Send recovery probes to verify."
          : `Local ${kind} fault armed for 30 seconds.`,
      );
      await refresh();
    } catch (e) {
      setFeedback((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function probe() {
    setBusy(true);
    try {
      for (let i = 0; i < 10; i++) await fetch("/api/events");
      setFeedback("10 real GET /events probes completed.");
      await refresh();
    } finally {
      setBusy(false);
    }
  }
  const s = summary;
  const active = incidents.filter((i) => !i.end);
  const chartData =
    s?.history.map((h) => ({
      ...h,
      label: time(h.at),
      latency: h.p95 === null ? null : h.p95 * 1000,
      error: h.error_rate === null ? null : h.error_rate * 100,
    })) || [];
  const kpis = s
    ? [
        {
          label: "Request throughput",
          value: `${s.rps.toFixed(2)}`,
          unit: "req/s",
          detail: `${s.requests} requests in window`,
          icon: Zap,
          color: "blue",
        },
        {
          label: "Request availability",
          value: pct(s.availability),
          detail: "Objective ≥ 99.00%",
          icon: ShieldCheck,
          color: "green",
        },
        {
          label: "p95 response time",
          value: ms(s.p95),
          detail: `p50 ${ms(s.p50)} · p99 ${ms(s.p99)}`,
          icon: Clock3,
          color: "purple",
        },
        {
          label: "HTTP 5xx error rate",
          value: pct(s.error_rate),
          detail: `${s.errors} server errors in window`,
          icon: Activity,
          color: s.errors ? "red" : "green",
        },
      ]
    : [];
  return (
    <div className="app">
      <aside className={menu ? "sidebar open" : "sidebar"}>
        <a className="brand" href="#" onClick={() => setPage(0)}>
          <span className="brand-mark">
            <Activity size={25} />
          </span>
          <span>
            EventPulse<span className="brand-sub">RELIABILITY PLATFORM</span>
          </span>
        </a>
        <div className="workspace">
          <span className="workspace-icon">EP</span>
          <div>
            Event platform<small>Local development</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {pages.map((p, i) => {
            const Icon = icons[i];
            return (
              <button
                key={p}
                className={i === page ? "nav active" : "nav"}
                onClick={() => {
                  setPage(i);
                  setMenu(false);
                }}
              >
                <Icon size={18} />
                {p}
                {i === 2 && active.length > 0 && (
                  <span className="count">{active.length}</span>
                )}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <div className="system">
            <span className={`dot ${error ? "red" : "green"}`} />
            <div>
              {error ? "API unreachable" : "Telemetry connected"}
              <small>Single-instance · v{s?.version || "1.0.0"}</small>
            </div>
          </div>
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            <ExternalLink size={16} /> Open Grafana <ArrowUpRight size={15} />
          </a>
          <div className="profile">
            <span>LO</span>
            <div>
              Local operator<small>EventPulse SRE lab</small>
            </div>
            <ShieldCheck size={16} />
          </div>
        </div>
      </aside>
      <div className="main">
        <header>
          <button
            className="mobile-toggle"
            aria-label="Toggle navigation"
            onClick={() => setMenu(!menu)}
          >
            {menu ? <X /> : <Menu />}
          </button>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <span>{pages[page]}</span>
          </div>
          <div className="header-right">
            <span className="pill neutral">LOCAL ENVIRONMENT</span>
            <span className="header-divider" />
            <span className="small muted">API v{s?.version || "—"}</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">OBSERVABILITY / EVENT PLATFORM</div>
              <h1>{pages[page]}</h1>
              <p>
                {
                  [
                    "A clear view of your service. From first request to full recovery.",
                    "Follow every request, endpoint and dependency.",
                    "Investigate user impact and document the path to recovery.",
                    "Measure reliability against explicit, request-based objectives.",
                    "Controlled failures. Observable impact. Verified recovery.",
                    "Reproducible experiments, independently labeled outcomes.",
                    "Offline wireless feature validation, packet evidence and cross-layer investigation.",
                  ][page]
                }
              </p>
            </div>
            <button className="btn" onClick={() => void refresh()}>
              <RefreshCw size={15} /> Refresh
            </button>
          </div>
          {error && (
            <div role="alert" className="banner error">
              <Siren size={18} />
              <div>
                Unable to refresh telemetry: {error}.{" "}
                {s
                  ? "Last successful values remain visible."
                  : "Start the API on port 8000."}
              </div>
              <button className="btn" onClick={() => void refresh()}>
                Retry
              </button>
            </div>
          )}
          {!s && !error && (
            <div className="loading" role="status">
              <RefreshCw className="spin" /> Connecting to the telemetry stream…
            </div>
          )}
          {s && (
            <>
              {page !== 6 && (
                <div className="status-strip">
                  <span
                    className={`pill ${error || s.status === "degraded" ? "red" : s.requests ? "green" : "neutral"}`}
                  >
                    <span className="dot" />
                    {error ? "STALE TELEMETRY" : s.status.toUpperCase()}
                  </span>
                  <span className="small">event-registration-api</span>
                  <span className="muted small">·</span>
                  <span className="muted small">
                    Window: last {s.window_seconds}s
                  </span>
                  <span className="live-note">
                    <span className="dot blue" /> Live request data ·{" "}
                    {updated?.toLocaleTimeString()}
                  </span>
                </div>
              )}
              {s.sample_retention_truncated && (
                <div className="banner error">
                  Sample buffer reached capacity. Window statistics may be
                  incomplete.
                </div>
              )}
              {page === 0 && (
                <>
                  <div className="kpi-grid">
                    {kpis.map((k) => (
                      <div className="kpi" key={k.label}>
                        <div className="kpi-top">
                          <span>{k.label}</span>
                          <span className={`icon-box ${k.color}`}>
                            <k.icon size={16} />
                          </span>
                        </div>
                        <div className="kpi-value">
                          {k.value}
                          <small>{k.unit}</small>
                        </div>
                        <div className="kpi-detail">{k.detail}</div>
                      </div>
                    ))}
                  </div>
                  <div className="charts-grid">
                    <Panel
                      title="Request activity"
                      sub="Completed business requests per second"
                      tag={`${s.window_seconds}s rolling window`}
                    >
                      <div className="legend">
                        <span className="dot blue" />
                        Throughput{" "}
                        <span className="muted">/ events & registrations</span>
                      </div>
                      {s.requests ? (
                        <div className="chart">
                          <ResponsiveContainer width="100%" height={245}>
                            <AreaChart data={chartData}>
                              <defs>
                                <linearGradient
                                  id="blue"
                                  x1="0"
                                  y1="0"
                                  x2="0"
                                  y2="1"
                                >
                                  <stop
                                    offset="0%"
                                    stopColor="#38BDF8"
                                    stopOpacity={0.3}
                                  />
                                  <stop
                                    offset="100%"
                                    stopColor="#38BDF8"
                                    stopOpacity={0}
                                  />
                                </linearGradient>
                              </defs>
                              <CartesianGrid
                                stroke="#203047"
                                vertical={false}
                              />
                              <XAxis
                                dataKey="label"
                                tick={{ fill: "#8d9db5", fontSize: 10 }}
                                minTickGap={45}
                                axisLine={false}
                                tickLine={false}
                              />
                              <YAxis
                                tick={{ fill: "#8d9db5", fontSize: 10 }}
                                width={35}
                                axisLine={false}
                                tickLine={false}
                              />
                              <Tooltip
                                contentStyle={{
                                  background: "#111C2E",
                                  border: "1px solid #30435c",
                                  borderRadius: 10,
                                }}
                              />
                              <Area
                                type="monotone"
                                dataKey="rps"
                                stroke="#38BDF8"
                                fill="url(#blue)"
                                strokeWidth={2}
                                isAnimationActive={false}
                              />
                            </AreaChart>
                          </ResponsiveContainer>
                        </div>
                      ) : (
                        <Empty>
                          No business requests in this window. Send probes to
                          begin.
                        </Empty>
                      )}
                    </Panel>
                    <Panel
                      title="Reliability at a glance"
                      sub="Request-based service objectives"
                    >
                      <div className="reliability-ring">
                        <div
                          className="ring"
                          style={{
                            background: `conic-gradient(#38bdf8 ${Math.max(0, Math.min(100, (s.budget_remaining ?? 0) * 100))}%, #243349 0)`,
                          }}
                        >
                          <div>
                            <strong>
                              {s.budget_remaining === null
                                ? "—"
                                : `${Math.max(0, s.budget_remaining * 100).toFixed(0)}%`}
                            </strong>
                            <span>budget remaining</span>
                          </div>
                        </div>
                      </div>
                      <div className="reliability-row">
                        <span>Availability objective</span>
                        <b>99.00%</b>
                      </div>
                      <div className="reliability-row">
                        <span>Active incidents</span>
                        <b
                          className={active.length ? "red-text" : "green-text"}
                        >
                          {active.length}
                        </b>
                      </div>
                      <button className="text-btn" onClick={() => setPage(3)}>
                        View SLO dashboard <ChevronRight size={14} />
                      </button>
                    </Panel>
                  </div>
                  <div className="two-col">
                    <Panel
                      title="Service health"
                      sub="Application and dependency signals"
                    >
                      <div className="health-row">
                        <span className="service-icon blue">
                          <Activity size={19} />
                        </span>
                        <div>
                          <b>Registration API</b>
                          <small>FastAPI · {s.version}</small>
                        </div>
                        <span
                          className={`pill ${s.status === "degraded" ? "red" : "green"}`}
                        >
                          {s.status}
                        </span>
                      </div>
                      <div className="health-row">
                        <span className="service-icon purple">
                          <Database size={19} />
                        </span>
                        <div>
                          <b>Application database</b>
                          <small>Live SELECT 1 readiness probe</small>
                        </div>
                        <span
                          className={`pill ${s.database_ready ? "green" : "red"}`}
                        >
                          {s.database_ready ? "Ready" : "Unavailable"}
                        </span>
                      </div>
                      <div className="panel-footer">
                        <Clock3 size={13} /> Process uptime:{" "}
                        {Math.floor(s.uptime)}s <span>Fault: {s.fault}</span>
                      </div>
                    </Panel>
                    <Panel
                      title="Incident feed"
                      sub="Grouped by impact signal"
                      tag={`${active.length} active`}
                    >
                      {incidents.length ? (
                        incidents.slice(0, 3).map((i) => (
                          <button
                            className="incident-compact"
                            key={i.id}
                            onClick={() => setPage(2)}
                          >
                            <span
                              className={`dot ${i.end ? "green" : "red"}`}
                            />
                            <div>
                              <b>
                                {i.kind === "availability"
                                  ? "Elevated server errors"
                                  : "Latency objective exceeded"}
                              </b>
                              <small>
                                {time(i.start)} · {i.severity}
                              </small>
                            </div>
                            <span className={`pill ${i.end ? "green" : "red"}`}>
                              {i.status}
                            </span>
                          </button>
                        ))
                      ) : (
                        <Empty>
                          No incidents detected. Healthy is a good place to be.
                        </Empty>
                      )}
                    </Panel>
                  </div>
                  <div className="demo-strip">
                    <Terminal size={19} />
                    <div>
                      <b>Make the signals move</b>
                      <small>
                        Send real requests, then introduce a controlled failure
                        in the lab.
                      </small>
                    </div>
                    <button
                      className="btn"
                      disabled={busy}
                      onClick={() => void probe()}
                    >
                      Send 10 probes <ArrowUpRight size={14} />
                    </button>
                    <button className="text-btn" onClick={() => setPage(4)}>
                      Open lab <ChevronRight size={14} />
                    </button>
                  </div>
                </>
              )}
              {page === 1 && (
                <>
                  <div className="two-col">
                    <Panel
                      title="Endpoint performance"
                      sub={`Measured over the last ${s.window_seconds} seconds`}
                    >
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Endpoint</th>
                              <th>Requests</th>
                              <th>p95</th>
                              <th>5xx</th>
                            </tr>
                          </thead>
                          <tbody>
                            {s.endpoints.map((e) => (
                              <tr key={e.route}>
                                <td>
                                  <code>{e.route}</code>
                                </td>
                                <td>{e.requests}</td>
                                <td>{ms(e.p95)}</td>
                                <td>{pct(e.error_rate)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </Panel>
                    <Panel
                      title="Latency distribution"
                      sub="Cumulative histogram bucket counts"
                    >
                      <ResponsiveContainer width="100%" height={240}>
                        <BarChart data={s.histogram}>
                          <CartesianGrid stroke="#203047" vertical={false} />
                          <XAxis
                            dataKey="le"
                            tick={{ fill: "#8d9db5", fontSize: 11 }}
                          />
                          <YAxis tick={{ fill: "#8d9db5", fontSize: 11 }} />
                          <Tooltip contentStyle={{ background: "#111C2E" }} />
                          <Bar
                            dataKey="count"
                            fill="#38bdf8"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                      <p className="footnote">
                        Bucket upper bounds in seconds; +Inf is exported in
                        /metrics.
                      </p>
                    </Panel>
                  </div>
                  <Panel
                    title="Tail latency trend"
                    sub="p95 milliseconds per observed subwindow"
                  >
                    <ResponsiveContainer width="100%" height={220}>
                      <AreaChart data={chartData}>
                        <CartesianGrid stroke="#203047" vertical={false} />
                        <XAxis
                          dataKey="label"
                          minTickGap={45}
                          tick={{ fill: "#8d9db5", fontSize: 11 }}
                        />
                        <YAxis tick={{ fill: "#8d9db5", fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "#111C2E" }} />
                        <Area
                          dataKey="latency"
                          stroke="#a78bfa"
                          fill="#a78bfa22"
                          isAnimationActive={false}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Panel>
                  <Panel
                    title="API error trend"
                    sub="Percentage of requests returning HTTP 5xx"
                  >
                    <ResponsiveContainer width="100%" height={230}>
                      <AreaChart data={chartData}>
                        <CartesianGrid stroke="#203047" vertical={false} />
                        <XAxis
                          dataKey="label"
                          minTickGap={45}
                          tick={{ fill: "#8d9db5", fontSize: 11 }}
                        />
                        <YAxis tick={{ fill: "#8d9db5", fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: "#111C2E" }} />
                        <Area
                          dataKey="error"
                          stroke="#ef4444"
                          fill="#ef444422"
                          isAnimationActive={false}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </Panel>
                  <div className="banner">
                    <Database size={18} />
                    <span>
                      Database: {s.database_ready ? "ready" : "unavailable"} ·
                      OS process CPU and memory counters are exported to
                      Prometheus at /metrics. Open Grafana for resource time
                      series.
                    </span>
                  </div>
                </>
              )}
              {page === 2 && (
                <>
                  {!incidents.length ? (
                    <Panel
                      title="All clear"
                      sub="Incidents appear after a sustained user-impact signal"
                    >
                      <Empty>
                        No incidents yet. Use the fault lab to rehearse
                        detection and recovery.
                      </Empty>
                    </Panel>
                  ) : (
                    incidents.map((i) => (
                      <Panel
                        key={i.id}
                        title={`${i.severity} · ${i.kind === "availability" ? "Elevated HTTP errors" : "High request latency"}`}
                        tag={i.status}
                        sub={`${i.id.slice(0, 8)} · Started ${new Date(i.start * 1000).toLocaleString()}`}
                      >
                        <div className="incident-meta">
                          <span>
                            Trigger:{" "}
                            {i.kind === "latency"
                              ? ms(i.evidence.metric)
                              : pct(i.evidence.metric)}
                          </span>
                          <span>
                            {i.evidence.requests} requests /{" "}
                            {i.evidence.window_seconds}s
                          </span>
                          <span>Ended: {i.end ? time(i.end) : "ongoing"}</span>
                        </div>
                        <p className="footnote">
                          Affected: {i.evidence.endpoints.join(", ")} ·
                          Local-window detector; Prometheus alerts are separate.
                        </p>
                        <div className="timeline">
                          {i.timeline.map((t, n) => (
                            <div key={n}>
                              <span className="dot blue" />
                              <time>{time(t.at)}</time>
                              <b>{t.action}</b>
                              <span>{t.detail}</span>
                            </div>
                          ))}
                        </div>
                        <p className="footnote">
                          Investigation:{" "}
                          {i.notes || "No investigation notes recorded."}
                        </p>
                        {s.faults_enabled && (
                          <div className="note-form">
                            <input
                              aria-label={`Investigation note ${i.id}`}
                              placeholder="Add investigation notes…"
                              value={note}
                              onChange={(e) => setNote(e.target.value)}
                            />
                            <button
                              className="btn"
                              onClick={async () => {
                                try {
                                  await api(`/operations/incidents/${i.id}`, {
                                    method: "PATCH",
                                    headers: {
                                      "Content-Type": "application/json",
                                      "X-Lab-Token": token,
                                    },
                                    body: JSON.stringify({ notes: note }),
                                  });
                                  setNote("");
                                  await refresh();
                                } catch (e) {
                                  setFeedback((e as Error).message);
                                }
                              }}
                            >
                              Save note
                            </button>
                          </div>
                        )}
                      </Panel>
                    ))
                  )}
                </>
              )}
              {page === 3 && (
                <>
                  <div className="kpi-grid">
                    <div className="kpi">
                      <span>Availability SLI / objective</span>
                      <div className="kpi-value">{pct(s.availability)}</div>
                      <small>Target ≥99% non-5xx responses</small>
                    </div>
                    <div className="kpi">
                      <span>Latency SLI / objective</span>
                      <div className="kpi-value">{pct(s.latency_sli)}</div>
                      <small>Target ≥95% responses ≤500ms</small>
                    </div>
                    <div className="kpi">
                      <span>Remaining error budget</span>
                      <div className="kpi-value">{pct(s.budget_remaining)}</div>
                      <small>Negative means budget exceeded</small>
                    </div>
                    <div className="kpi">
                      <span>Availability burn rate</span>
                      <div className="kpi-value">
                        {s.burn_rate?.toFixed(2) ?? "—"}×
                      </div>
                      <small>Observed error ratio / 1% allowance</small>
                    </div>
                  </div>
                  <Panel
                    title="SLI history"
                    sub="Observed subwindows; gaps mean no traffic"
                  >
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Window start</th>
                            <th>Requests</th>
                            <th>Availability</th>
                            <th>p95 latency</th>
                            <th>Burn rate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {s.history
                            .filter((h) => h.requests > 0)
                            .map((h) => (
                              <tr key={h.at}>
                                <td>{time(h.at)}</td>
                                <td>{h.requests}</td>
                                <td>{pct(h.availability)}</td>
                                <td>{ms(h.p95)}</td>
                                <td>{h.burn_rate?.toFixed(2)}×</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                      {!s.requests && (
                        <Empty>
                          Insufficient traffic for an SLI. No availability is
                          assumed.
                        </Empty>
                      )}
                    </div>
                  </Panel>
                  <div className="two-col">
                    <Panel
                      title="Local demonstration detector"
                      sub="Evaluates every 500ms"
                    >
                      <p className="explanation">
                        At least 5 business requests in the rolling window.
                        Error ratio &gt;5% or p95 &gt;500ms, sustained for 1
                        second. Incidents group by signal and resolve when the
                        condition clears. Resolution without traffic is not
                        proof of recovery.
                      </p>
                    </Panel>
                    <Panel
                      title="Prometheus alert policy"
                      sub="Independent 5m + 1h burn-rate windows"
                    >
                      <p className="explanation">
                        Fast burn: both windows exceed 14.4×, with ≥100 requests
                        in 5m, sustained for 2m. Latency: p95 &gt;500ms with
                        ≥100 requests in 5m, sustained for 2m. Alertmanager
                        groups by alert name and service.
                      </p>
                    </Panel>
                  </div>
                </>
              )}
              {page === 4 && (
                <>
                  <div
                    className={`banner ${s.faults_enabled ? "" : "warning"}`}
                  >
                    <ShieldCheck size={21} />
                    <span>
                      {s.faults_enabled
                        ? "Local lab enabled. A token and loopback connection are required. Faults expire automatically."
                        : "Fault injection is disabled by default. See FAULT_INJECTION.md to opt in on your local machine."}
                    </span>
                  </div>
                  <Panel
                    title="Experiment controls"
                    sub="Synthetic traffic only · maximum fault duration 120 seconds"
                  >
                    <div className="lab-inputs">
                      <label>
                        Local lab token
                        <input
                          type="password"
                          autoComplete="off"
                          value={token}
                          onChange={(e) => setToken(e.target.value)}
                          placeholder="Enter your FAULT_TOKEN"
                        />
                      </label>
                      <label>
                        Injected delay: {delay}ms
                        <input
                          type="range"
                          min="100"
                          max="3000"
                          step="50"
                          value={delay}
                          onChange={(e) => setDelay(+e.target.value)}
                        />
                      </label>
                      <button
                        className="btn"
                        disabled={busy}
                        onClick={() => void probe()}
                      >
                        Send real probes
                      </button>
                      <button
                        className="btn danger"
                        disabled={!s.faults_enabled || busy}
                        onClick={() => void fault("none")}
                      >
                        Clear fault
                      </button>
                    </div>
                    <div className="fault-grid">
                      {[
                        {
                          kind: "latency",
                          name: "Latency spike",
                          desc: "Delay business requests; observe tail latency.",
                        },
                        {
                          kind: "http500",
                          name: "HTTP 500 burst",
                          desc: "Return server errors; consume the error budget.",
                        },
                        {
                          kind: "dependency",
                          name: "Dependency timeout",
                          desc: "Simulate a slow downstream and HTTP 504.",
                        },
                        {
                          kind: "database",
                          name: "Database unavailable",
                          desc: "Simulate readiness failure and HTTP 503. Does not stop PostgreSQL.",
                        },
                        {
                          kind: "warning",
                          name: "Noisy warnings",
                          desc: "Emit warning logs without altering responses.",
                        },
                      ].map((f) => (
                        <button
                          className="fault-card"
                          disabled={!s.faults_enabled || busy}
                          onClick={() => void fault(f.kind)}
                          key={f.kind}
                        >
                          <FlaskConical size={22} />
                          <b>{f.name}</b>
                          <span>{f.desc}</span>
                          <small>
                            Arm for 30 seconds <ArrowUpRight size={13} />
                          </small>
                        </button>
                      ))}
                    </div>
                  </Panel>
                  <Panel
                    title="Rehearsal workflow"
                    sub="A repeatable incident lifecycle"
                  >
                    <div className="workflow">
                      {[
                        "1. Send baseline requests",
                        "2. Arm a local fault",
                        "3. Send affected requests",
                        "4. Inspect the incident",
                        "5. Clear & send recovery probes",
                      ].map((t) => (
                        <div key={t}>
                          <Check size={15} />
                          {t}
                        </div>
                      ))}
                    </div>
                  </Panel>
                </>
              )}
              {page === 5 && (
                <>
                  <Panel
                    title="Experiment evidence"
                    sub={experiments?.source || "No experiments available"}
                    tag={`${experiments?.runs.length || 0} completed`}
                  >
                    <div className="export-row">
                      <a
                        className="btn"
                        href="/api/operations/experiments?format=json"
                        download
                      >
                        <Download size={15} /> JSON
                      </a>
                      <a
                        className="btn"
                        href="/api/operations/experiments?format=csv"
                        download
                      >
                        <Download size={15} /> CSV
                      </a>
                    </div>
                    {experiments?.runs.length ? (
                      <>
                        <div className="experiment-summary">
                          {Object.entries(experiments.summary).map(
                            ([key, value]) => (
                              <div key={key}>
                                <span>{key.replaceAll("_", " ")}</span>
                                <b>
                                  {typeof value === "object"
                                    ? JSON.stringify(value)
                                    : String(value)}
                                </b>
                              </div>
                            ),
                          )}
                        </div>
                        <div className="table-wrap">
                          <table>
                            <thead>
                              <tr>
                                <th>Scenario</th>
                                <th>Split</th>
                                <th>Truth / alert</th>
                                <th>Success</th>
                                <th>p95</th>
                                <th>Detection</th>
                                <th>Recovery</th>
                              </tr>
                            </thead>
                            <tbody>
                              {experiments.runs.map((r, i) => (
                                <tr key={i}>
                                  <td>{r.scenario}</td>
                                  <td>{r.split}</td>
                                  <td>
                                    {String(r.expected_impact)} /{" "}
                                    {String(r.detected)}
                                  </td>
                                  <td>{pct(r.success_rate)}</td>
                                  <td>{ms(r.p95_seconds)}</td>
                                  <td>
                                    {r.detection_seconds == null
                                      ? "—"
                                      : `${r.detection_seconds.toFixed(2)}s`}
                                  </td>
                                  <td>
                                    {r.recovery_seconds == null
                                      ? "—"
                                      : `${r.recovery_seconds.toFixed(2)}s`}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    ) : (
                      <Empty>
                        No completed experiments. Run python scripts/evaluate.py
                        against a local lab.
                      </Empty>
                    )}
                  </Panel>
                  {!!experiments?.configuration_comparison?.length && (
                    <Panel
                      title="Monitoring configuration comparison"
                      sub="Offline scenario aggregates on the same requests; does not replay hold periods or timing"
                    >
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Configuration</th>
                              <th>Precision</th>
                              <th>Recall</th>
                              <th>False alerts</th>
                            </tr>
                          </thead>
                          <tbody>
                            {experiments.configuration_comparison.map((c) => (
                              <tr key={c.configuration}>
                                <td>{c.configuration}</td>
                                <td>{pct(c.precision)}</td>
                                <td>{pct(c.recall)}</td>
                                <td>{c.false_alerts}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="footnote">
                        Wilson intervals are included in the JSON evidence.
                        Small synthetic samples do not establish production
                        accuracy.
                      </p>
                    </Panel>
                  )}
                </>
              )}
              {page === 6 && <WirelessLab />}
              {feedback && (
                <div role="status" className="banner">
                  <Activity size={18} />
                  {feedback}
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              <Activity size={13} /> EventPulse SRE{" "}
              <span className="muted">/ Reliability is a practice.</span>
            </span>
            <span>Measured locally. No production claims.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
