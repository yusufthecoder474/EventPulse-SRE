import { useEffect, useState } from "react";
import {
  Wifi,
  Radio,
  ShieldCheck,
  ArrowRight,
  Play,
  Download,
  RefreshCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  FileSearch,
  Server,
  LogOut,
  ChevronRight,
  Activity,
  LockKeyhole,
} from "lucide-react";
import "./wireless.css";
import WirelessV3 from "./WirelessV3";
type Scenario = {
  id: string;
  title: string;
  objective: string;
  preconditions: string[];
  fixture: string;
  evidence_type: string;
  expected_classifications: string[];
  reproduction: string;
};
type AP = {
  id: string;
  name: string;
  ssid: string;
  channel: number;
  bssid: string;
  status: string;
};
type Event = {
  direction?: string;
  frame_subtype?: string;
  event_id: string;
  timestamp_us: number;
  capture_timestamp?: string;
  client: string;
  ap: string;
  kind: string;
  code: number;
  origin: string;
  link_layer: string;
  ssid?: string;
  explanation?: string;
  missing_fields: string[];
};
type Client = {
  client: string;
  ap: string;
  state: string;
  classification: string;
  explanation: string;
  association_latency_ms: number | null;
  controller_lag_ms: number | null;
  invalid_transition: boolean;
  eapol_messages_observed: number[];
  key_exchange: string;
  sae_exchange: string;
  findings: string[];
};
type Run = {
  id: string;
  created_at: number;
  scenario: Scenario;
  verdict: string;
  actual_classifications: string[];
  events: Event[];
  analysis: {
    engine: string;
    input_events: number;
    processed_events: number;
    duplicate_events: number;
    out_of_order_pairs: number;
    clients: Client[];
    analysis_duration_ms: number;
  };
  extraction: { parsing_duration_ms: number | null; limitations: string[] };
  total_duration_ms: number;
};
type History = {
  id: string;
  created_at: number;
  scenario_id: string;
  title: string;
  verdict: string;
  classifications: string[];
  duration_ms: number | null;
};
type Capabilities = {
  cpp_analyzer: boolean;
  tshark: boolean;
  notice: string;
  guest_limits: {
    session_seconds: number;
    runs_retained: number;
    operations_per_minute: number;
  };
};
const tabs = [
  "Wireless overview",
  "Virtual access points",
  "Client connection timeline",
  "Packet trace explorer",
  "Automated test scenarios",
  "Failure investigation",
  "Analytics and reports",
];
const labels = (s: string) => s.replaceAll("_", " ");
const milliseconds = (n: number | null | undefined) =>
  n == null ? "Not measured" : `${n.toFixed(2)} ms`;
async function call<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch("/api/wireless-lab" + path, {
    credentials: "same-origin",
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Wireless-Demo": "1",
      ...options?.headers,
    },
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({ error: r.statusText }));
    throw new Error(d.error || `HTTP ${r.status}`);
  }
  return r.json();
}
function Card({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="wl-card">
      <div className="wl-card-head">
        <h3>{title}</h3>
        {sub && <p>{sub}</p>}
      </div>
      {children}
    </section>
  );
}
export default function WirelessLab() {
  const [guest, setGuest] = useState(false),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [tab, setTab] = useState(0),
    [caps, setCaps] = useState<Capabilities | null>(null),
    [aps, setAPs] = useState<AP[]>([]),
    [scenarios, setScenarios] = useState<Scenario[]>([]),
    [history, setHistory] = useState<History[]>([]),
    [run, setRun] = useState<Run | null>(null),
    [filter, setFilter] = useState(""),
    [ascending, setAscending] = useState(true),
    [apName, setAPName] = useState(""),
    [message, setMessage] = useState("");
  async function refresh() {
    const [a, s, h, c] = await Promise.all([
      call<AP[]>("/aps"),
      call<Scenario[]>("/scenarios"),
      call<History[]>("/runs"),
      call<Capabilities>("/capabilities"),
    ]);
    setAPs(a);
    setScenarios(s);
    setHistory(h);
    setCaps(c);
    return { h, c };
  }
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await call("/session");
        if (!active) return;
        setGuest(true);
        const { h } = await refresh();
        if (active && h.length) setRun(await call<Run>("/runs/" + h[0].id));
      } catch (e) {
        if (
          active &&
          !String(e).includes("Guest") &&
          !String(e).includes("expired")
        )
          setError((e as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);
  async function enter() {
    setBusy(true);
    setError("");
    try {
      await call("/guest", { method: "POST", body: "{}" });
      setGuest(true);
      const { c } = await refresh();
      if (c.cpp_analyzer) {
        const data = await call<Run>("/runs", {
          method: "POST",
          body: JSON.stringify({ scenario_id: c.tshark ? "A" : "H" }),
        });
        setRun(data);
        await refresh();
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function execute(id: string, switchTo?: number) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      setRun(
        await call<Run>("/runs", {
          method: "POST",
          body: JSON.stringify({ scenario_id: id }),
        }),
      );
      await refresh();
      if (switchTo !== undefined) setTab(switchTo);
      setMessage(`Scenario ${id} executed through the C++17 analyzer.`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function suite() {
    setBusy(true);
    setError("");
    let completed = 0;
    try {
      for (const s of scenarios) {
        setRun(
          await call<Run>("/runs", {
            method: "POST",
            body: JSON.stringify({ scenario_id: s.id }),
          }),
        );
        completed++;
      }
      setMessage(
        `${completed} scenarios completed. PASS means the expected behavior was reproduced, including expected failures.`,
      );
    } catch (e) {
      setError(`${completed} completed. ${(e as Error).message}`);
    } finally {
      await refresh().catch(() => {});
      setBusy(false);
    }
  }
  async function selectRun(id: string) {
    setBusy(true);
    try {
      setRun(await call<Run>("/runs/" + id));
      setTab(5);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (loading)
    return (
      <div className="wl-loading" role="status">
        <RefreshCw className="spin" /> Restoring demo workspace…
      </div>
    );
  const rows = (run?.events || [])
    .filter((e) =>
      [e.kind, e.client, e.ap, e.ssid || "", e.origin]
        .join(" ")
        .toLowerCase()
        .includes(filter.toLowerCase()),
    )
    .sort((a, b) =>
      ascending
        ? a.timestamp_us - b.timestamp_us
        : b.timestamp_us - a.timestamp_us,
    );
  const client = run?.analysis.clients[0];
  const passed = history.filter((h) => h.verdict === "pass").length;
  const times = history
    .map((h) => h.duration_ms)
    .filter((n): n is number => n !== null)
    .sort((a, b) => a - b);
  const p95 = times.length ? times[Math.ceil(times.length * 0.95) - 1] : null;
  return (
    <div className="wireless-lab">
      {error && (
        <div className="banner error" role="alert">
          <AlertTriangle size={18} />
          {error}
          <button
            className="btn"
            onClick={() => {
              setError("");
              if (guest) void refresh().catch((e) => setError(e.message));
            }}
          >
            Dismiss / retry
          </button>
        </div>
      )}
      {!guest ? (
        <>
          <div className="wl-entry">
            <div className="wl-entry-copy">
              <span className="wl-kicker">
                <Radio size={13} /> ENGINEERING LAB / OFFLINE & SYNTHETIC
              </span>
              <h2>
                Follow the connection.
                <br />
                <span>Find the failing layer.</span>
              </h2>
              <p>
                A wireless investigation workspace for packet evidence, C++
                state analysis and repeatable feature validation. Explore the
                complete demo without an account.
              </p>
              <button
                className="wl-primary"
                disabled={busy}
                onClick={() => void enter()}
              >
                {busy ? (
                  <RefreshCw className="spin" size={18} />
                ) : (
                  <ArrowRight size={18} />
                )}{" "}
                Continue as Guest
              </button>
              <div className="wl-entry-note">
                <LockKeyhole size={13} /> No email. No password. Server-issued
                temporary session.
              </div>
            </div>
            <div
              className="wl-topology"
              aria-label="Simulated client to access point to controller"
            >
              <span className="wl-grid-label">CONTROLLED LABORATORY</span>
              <div className="wl-node">
                <Wifi />
                <b>Synthetic client</b>
                <small>Authentication · association</small>
              </div>
              <div className="wl-connector">
                <span />
                <ChevronRight size={15} />
              </div>
              <div className="wl-node accent">
                <Radio />
                <b>Virtual access point</b>
                <small>Packet and event evidence</small>
              </div>
              <div className="wl-connector">
                <span />
                <ChevronRight size={15} />
              </div>
              <div className="wl-node">
                <Server />
                <b>Controller model</b>
                <small>Status correlation</small>
              </div>
              <span className="wl-diagram-foot">
                No live radios · No Cisco equipment · No traffic capture
              </span>
            </div>
          </div>
          <div className="wl-feature-grid">
            {[
              {
                icon: FileSearch,
                title: "Inspect the evidence",
                text: "Generated 802.11 PCAPs and clearly labeled event fixtures.",
              },
              {
                icon: Activity,
                title: "Validate the behavior",
                text: "A real C++17 analyzer processes normalized Python events.",
              },
              {
                icon: ShieldCheck,
                title: "Stay inside the lab",
                text: "Bounded, isolated guest runs. No device or OS controls.",
              },
            ].map((f) => (
              <div className="wl-feature" key={f.title}>
                <f.icon size={20} />
                <h3>{f.title}</h3>
                <p>{f.text}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <>
          <div className="wl-demo-bar">
            <span className="pill blue">
              <span className="dot" /> DEMO MODE
            </span>
            <span>Synthetic APs and clients · isolated guest workspace</span>
            <button
              className="text-btn"
              onClick={async () => {
                try {
                  await call("/session", { method: "DELETE" });
                  setGuest(false);
                  setRun(null);
                  setHistory([]);
                } catch (e) {
                  setError((e as Error).message);
                }
              }}
            >
              <LogOut size={13} /> End demo
            </button>
          </div>
          <nav className="wl-tabs" aria-label="WirelessLab sections">
            {tabs.map((t, i) => (
              <button
                key={t}
                aria-current={tab === i ? "page" : undefined}
                onClick={() => setTab(i)}
                className={tab === i ? "selected" : ""}
              >
                {t}
              </button>
            ))}
          </nav>
          <div className="wl-heading">
            <div>
              <span className="wl-kicker">
                WIRELESSLAB / {String(tab + 1).padStart(2, "0")}
              </span>
              <h2>{tabs[tab]}</h2>
            </div>
            <button
              className="btn"
              disabled={busy}
              onClick={() => void refresh().catch((e) => setError(e.message))}
            >
              <RefreshCw size={14} /> Refresh workspace
            </button>
          </div>
          {caps && (!caps.cpp_analyzer || !caps.tshark) && (
            <div className="banner warning">
              <AlertTriangle size={16} />
              {!caps.cpp_analyzer
                ? "C++ analyzer is not built. See Windows/Linux setup."
                : "TShark unavailable: JSON-event scenarios work; packet scenarios require TShark."}
            </div>
          )}
          <WirelessV3
            view={tab}
            selected={run}
            onResult={(value) => {
              setRun(value as Run);
              void refresh();
            }}
          />
          {tab === 0 && (
            <>
              <div className="wl-kpis">
                {[
                  {
                    label: "Virtual AP inventory",
                    value: aps.length,
                    sub: "Synthetic inventory, not live probes",
                  },
                  {
                    label: "Scenario definitions",
                    value: scenarios.length,
                    sub: "Five PCAP + five event-based cases",
                  },
                  {
                    label: "Validated runs",
                    value: `${passed} / ${history.length}`,
                    sub: "Retained history in this guest session",
                  },
                  {
                    label: "Latest engine",
                    value: run?.analysis.engine || "Not run",
                    sub: run
                      ? `${run.analysis.processed_events} events processed`
                      : "No analysis has been executed",
                  },
                ].map((k) => (
                  <div className="wl-kpi" key={k.label}>
                    <span>{k.label}</span>
                    <strong>{k.value}</strong>
                    <small>{k.sub}</small>
                  </div>
                ))}
              </div>
              <div className="wl-two">
                <Card
                  title="Connection investigation"
                  sub="The current run is computed, not a static mockup"
                >
                  <div className="wl-result-stage">
                    <span className="wl-stage-icon">
                      <Wifi size={27} />
                    </span>
                    <div>
                      <small>
                        SCENARIO {run?.scenario.id || "—"} /{" "}
                        {run?.scenario.evidence_type === "generated_pcap"
                          ? "GENERATED PCAP"
                          : "SYNTHETIC EVENTS"}
                      </small>
                      <h3>
                        {client
                          ? labels(client.classification)
                          : "No investigation yet"}
                      </h3>
                      <p>
                        {client?.explanation ||
                          "Run a scenario to collect analysis evidence."}
                      </p>
                    </div>
                    <span
                      className={`pill ${run?.verdict === "pass" ? "green" : "neutral"}`}
                    >
                      Validation {run?.verdict || "not run"}
                    </span>
                  </div>
                  <div className="wl-mini-signals">
                    <div>
                      <span>C++ analysis</span>
                      <b>{milliseconds(run?.analysis.analysis_duration_ms)}</b>
                    </div>
                    <div>
                      <span>Packet extraction</span>
                      <b>{milliseconds(run?.extraction.parsing_duration_ms)}</b>
                    </div>
                    <div>
                      <span>Input quality</span>
                      <b>
                        {run?.analysis.duplicate_events ?? 0} duplicate ·{" "}
                        {run?.analysis.out_of_order_pairs ?? 0} reordered
                      </b>
                    </div>
                  </div>
                  <button className="text-btn" onClick={() => setTab(5)}>
                    Open investigation <ArrowRight size={14} />
                  </button>
                </Card>
                <Card
                  title="Start a controlled experiment"
                  sub="Expected outcomes are declared before each run"
                >
                  <div className="wl-quick-actions">
                    {scenarios
                      .filter((s) => ["A", "B", "F", "J"].includes(s.id))
                      .map((s) => (
                        <button
                          key={s.id}
                          disabled={busy}
                          onClick={() => void execute(s.id, 5)}
                        >
                          <span>{s.id}</span>
                          <div>
                            <b>{s.title}</b>
                            <small>
                              {s.evidence_type === "generated_pcap"
                                ? "Generated packet evidence"
                                : "Synthetic state events"}
                            </small>
                          </div>
                          <Play size={14} />
                        </button>
                      ))}
                  </div>
                </Card>
              </div>
              <div className="banner">
                <ShieldCheck size={19} />
                <span>
                  Association success does not establish DHCP, DNS, internet
                  access or cryptographic correctness. This lab identifies the
                  demonstrated stage and reports missing evidence.
                </span>
              </div>
            </>
          )}
          {tab === 1 && (
            <>
              <div className="wl-feature-grid">
                {aps.map((a) => (
                  <div className="wl-ap" key={a.id}>
                    <div>
                      <span className="wl-stage-icon">
                        <Radio />
                      </span>
                      <span className="pill blue">SIMULATED</span>
                    </div>
                    <h3>{a.name}</h3>
                    <code>{a.bssid}</code>
                    <dl>
                      <div>
                        <dt>SSID</dt>
                        <dd>{a.ssid}</dd>
                      </div>
                      <div>
                        <dt>Logical channel</dt>
                        <dd>{a.channel}</dd>
                      </div>
                      <div>
                        <dt>Inventory state</dt>
                        <dd>{a.status}</dd>
                      </div>
                    </dl>
                    <small>No AP hardware is queried or configured.</small>
                  </div>
                ))}
              </div>
              <Card
                title="Register a virtual AP"
                sub="Changes only your synthetic demo inventory"
              >
                <form
                  className="wl-register"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setBusy(true);
                    try {
                      await call("/aps", {
                        method: "POST",
                        body: JSON.stringify({
                          name: apName,
                          ssid: "EventPulse-Lab",
                          channel: 6,
                        }),
                      });
                      setAPName("");
                      await refresh();
                      setMessage(
                        "Virtual AP added to your isolated demo. No network device was changed.",
                      );
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <label>
                    Virtual AP name
                    <input
                      required
                      maxLength={40}
                      pattern="[A-Za-z0-9 _-]+"
                      value={apName}
                      onChange={(e) => setAPName(e.target.value)}
                      placeholder="Research AP"
                    />
                  </label>
                  <button className="btn" disabled={busy}>
                    Add virtual AP
                  </button>
                </form>
              </Card>
            </>
          )}
          {tab === 2 && (
            <Card
              title="Client evidence timeline"
              sub={
                client
                  ? `${client.client} · ${client.ap}`
                  : "Run a scenario first"
              }
            >
              {run ? (
                <>
                  <div className="wl-protocol-track">
                    {[
                      "Discovery",
                      "Authentication",
                      "Association",
                      "Key evidence",
                      "IP configuration",
                      "DNS",
                    ].map((step, i) => {
                      const kinds = [
                        ["beacon", "probe_request"],
                        ["auth_ok", "auth_fail", "sae_confirm"],
                        ["assoc_ok", "assoc_reject"],
                        ["eapol_1", "eapol_4"],
                        ["dhcp_ack", "dhcp_fail"],
                        ["dns_ok", "dns_fail"],
                      ][i];
                      const seen = run.events.some((e) =>
                        kinds.includes(e.kind),
                      );
                      return (
                        <div key={step} className={seen ? "observed" : ""}>
                          <span>
                            {seen ? (
                              <CheckCircle2 size={16} />
                            ) : (
                              <span className="dot" />
                            )}
                          </span>
                          <b>{step}</b>
                          <small>
                            {seen ? "Evidence observed" : "Not established"}
                          </small>
                        </div>
                      );
                    })}
                  </div>
                  <div className="wl-timeline">
                    {[...run.events]
                      .sort((a, b) => a.timestamp_us - b.timestamp_us)
                      .map((e, i) => (
                        <div key={e.event_id + i}>
                          <span className="dot blue" />
                          <time>
                            {(
                              (e.timestamp_us -
                                Math.min(
                                  ...run.events.map((x) => x.timestamp_us),
                                )) /
                              1000
                            ).toFixed(1)}{" "}
                            ms
                          </time>
                          <div>
                            <b>{labels(e.kind)}</b>
                            <p>
                              {e.explanation || "Normalized event evidence."}
                            </p>
                            <small>
                              {e.origin} · {e.link_layer} ·{" "}
                              {e.direction === undefined
                                ? ""
                                : String(e.direction)}
                            </small>
                          </div>
                          <span className="pill neutral">
                            {e.code >= 0 ? `Code ${e.code}` : "No status code"}
                          </span>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <div className="empty">
                  No run selected. Run a scenario to populate the timeline.
                </div>
              )}
            </Card>
          )}
          {tab === 3 && (
            <>
              <Card
                title="Approved packet fixtures"
                sub="Generated offline; no real network traffic or credentials"
              >
                <div className="wl-fixture-actions">
                  {scenarios
                    .filter((s) => s.evidence_type === "generated_pcap")
                    .map((s) => (
                      <button
                        className="btn"
                        key={s.id}
                        disabled={busy}
                        onClick={() => void execute(s.id)}
                      >
                        <FileSearch size={14} /> Load {s.id}: {s.title}
                      </button>
                    ))}
                </div>
              </Card>
              <Card
                title="Trace explorer"
                sub={
                  run
                    ? `${run.scenario.fixture || run.scenario.title} · ${run.scenario.evidence_type} · ${run.events.length} normalized events`
                    : "No trace loaded"
                }
              >
                <div className="wl-filter">
                  <Search size={16} />
                  <input
                    aria-label="Filter packet events"
                    maxLength={128}
                    placeholder="Filter stage, client, AP, origin or SSID…"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  />
                  <button
                    className="btn"
                    onClick={() => setAscending(!ascending)}
                  >
                    Time {ascending ? "↑" : "↓"}
                  </button>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Capture/event time (UTC)</th>
                        <th>Type / stage</th>
                        <th>Source evidence</th>
                        <th>Client / AP</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((e, i) => (
                        <tr key={e.event_id + i}>
                          <td>
                            {new Date(e.timestamp_us / 1000)
                              .toISOString()
                              .slice(11, 23)}
                          </td>
                          <td>
                            <b>{labels(e.kind)}</b>
                            <small>
                              {e.frame_subtype || "No radio subtype"} ·{" "}
                              {e.link_layer}
                            </small>
                          </td>
                          <td>
                            {e.origin}
                            <small>
                              {e.missing_fields.length
                                ? `${e.missing_fields.length} missing fields`
                                : "Required addresses observed"}
                            </small>
                          </td>
                          <td>
                            <code>{e.client}</code>
                            <small>{e.ap}</small>
                          </td>
                          <td>{e.code >= 0 ? e.code : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!rows.length && (
                  <div className="empty">
                    No matching events. Load a packet fixture or clear the
                    filter.
                  </div>
                )}
                <p className="footnote">
                  Original capture timestamp strings are retained in JSON
                  exports. Payloads, passwords and key material are not
                  extracted. Ethernet EAPOL does not prove radio association.
                </p>
                {run?.scenario.evidence_type === "generated_pcap" && (
                  <a
                    className="btn wl-download"
                    href={`/api/wireless-lab/fixtures/${run.scenario.id}/capture`}
                  >
                    <Download size={14} /> Open this generated PCAP in Wireshark
                  </a>
                )}
              </Card>
            </>
          )}
          {tab === 4 && (
            <>
              <div className="wl-suite-heading">
                <p>
                  PASS means the expected scenario was reproduced. An expected
                  rejection is a passing validation test.
                </p>
                <button
                  className="wl-primary"
                  disabled={busy}
                  onClick={() => void suite()}
                >
                  <Play size={15} />
                  {busy ? "Executing…" : "Run ten-scenario suite"}
                </button>
              </div>
              <div className="wl-scenario-grid">
                {scenarios.map((s) => {
                  const latest = history.find((h) => h.scenario_id === s.id);
                  return (
                    <div className="wl-scenario" key={s.id}>
                      <div>
                        <span className="wl-scenario-id">{s.id}</span>
                        <span
                          className={`pill ${latest?.verdict === "pass" ? "green" : "neutral"}`}
                        >
                          {latest ? `Validation ${latest.verdict}` : "Not run"}
                        </span>
                      </div>
                      <h3>{s.title}</h3>
                      <p>{s.objective}</p>
                      <small>
                        {s.evidence_type === "generated_pcap"
                          ? "GENERATED PCAP"
                          : "SYNTHETIC EVENTS"}
                      </small>
                      <code>
                        Expected: {labels(s.expected_classifications[0])}
                      </code>
                      <button
                        className="btn"
                        disabled={busy}
                        onClick={() => void execute(s.id, 5)}
                      >
                        <Play size={13} /> Run scenario
                      </button>
                    </div>
                  );
                })}
              </div>
            </>
          )}
          {tab === 5 && (
            <>
              {run ? (
                <>
                  <Card
                    title={`Investigation · scenario ${run.scenario.id}`}
                    sub={`${run.scenario.title} · ${run.scenario.evidence_type}`}
                  >
                    <div className="wl-investigation">
                      <span className="wl-stage-icon">
                        <FileSearch size={25} />
                      </span>
                      <div>
                        <span
                          className={`pill ${run.verdict === "pass" ? "green" : run.verdict === "analysis_only" ? "neutral" : "red"}`}
                        >
                          {run.verdict === "analysis_only"
                            ? "Analysis only"
                            : `Validation ${run.verdict}`}
                        </span>
                        <h3>
                          {labels(client?.classification || "incomplete")}
                        </h3>
                        <p>{client?.explanation}</p>
                        <div className="wl-expectations">
                          <span>
                            Expected:{" "}
                            <b>
                              {run.scenario.expected_classifications
                                ?.map(labels)
                                .join(", ") || "No prescribed outcome"}
                            </b>
                          </span>
                          <span>
                            Observed:{" "}
                            <b>
                              {run.actual_classifications
                                .map(labels)
                                .join(", ")}
                            </b>
                          </span>
                        </div>
                      </div>
                    </div>
                  </Card>
                  <div className="wl-two">
                    <Card
                      title="Evidence and correlation"
                      sub="Statements grounded in this event sequence"
                    >
                      <ul className="wl-findings">
                        {client?.findings.length ? (
                          client.findings.map((f, i) => (
                            <li key={i}>
                              <AlertTriangle size={15} />
                              {f}
                            </li>
                          ))
                        ) : (
                          <li>
                            <CheckCircle2 size={15} />
                            No additional transition warnings for the current
                            event sequence.
                          </li>
                        )}
                      </ul>
                      <div className="wl-mini-signals">
                        <div>
                          <span>Association request → response</span>
                          <b>{milliseconds(client?.association_latency_ms)}</b>
                        </div>
                        <div>
                          <span>AP state → controller update</span>
                          <b>{milliseconds(client?.controller_lag_ms)}</b>
                        </div>
                        <div>
                          <span>Input quality</span>
                          <b>
                            {run.analysis.duplicate_events} duplicate /{" "}
                            {run.analysis.out_of_order_pairs} out-of-order pairs
                          </b>
                        </div>
                      </div>
                    </Card>
                    <Card
                      title="Security-stage evidence"
                      sub="Observations are not cryptographic verification"
                    >
                      <div className="wl-security">
                        <p>
                          <b>EAPOL-Key:</b>{" "}
                          {client?.eapol_messages_observed.length
                            ? client.eapol_messages_observed.join(" → ")
                            : "Not captured"}
                        </p>
                        <p>
                          {labels(
                            client?.key_exchange ||
                              "incomplete_or_not_captured",
                          )}
                        </p>
                        <p>
                          <b>SAE:</b>{" "}
                          {labels(
                            client?.sae_exchange ||
                              "incomplete_or_not_captured",
                          )}
                        </p>
                        <p>
                          WPA3 hardware testing is pending. This lab does not
                          verify passwords, MICs, keys or real AP
                          interoperability.
                        </p>
                      </div>
                    </Card>
                  </div>
                  <div className="wl-export">
                    <a
                      className="btn"
                      href={`/api/wireless-lab/runs/${run.id}/export?format=json`}
                    >
                      <Download size={14} /> Export investigation JSON
                    </a>
                    <a
                      className="btn"
                      href={`/api/wireless-lab/runs/${run.id}/export?format=csv`}
                    >
                      <Download size={14} /> Export events CSV
                    </a>
                  </div>
                </>
              ) : (
                <div className="empty">
                  No investigation selected. Execute a scenario or select a
                  historical run.
                </div>
              )}
            </>
          )}
          {tab === 6 && (
            <>
              <div className="wl-kpis">
                <div className="wl-kpi">
                  <span>Retained scenario runs</span>
                  <strong>{history.length}</strong>
                  <small>Maximum 20 per guest</small>
                </div>
                <div className="wl-kpi">
                  <span>Expected outcomes matched</span>
                  <strong>{passed}</strong>
                  <small>Includes expected failure scenarios</small>
                </div>
                <div className="wl-kpi">
                  <span>Observed validation failures</span>
                  <strong>
                    {history.filter((h) => h.verdict === "fail").length}
                  </strong>
                  <small>Not the same as client connection failures</small>
                </div>
                <div className="wl-kpi">
                  <span>Retained-run p95</span>
                  <strong>{p95 == null ? "—" : `${p95.toFixed(1)} ms`}</strong>
                  <small>Server run time; not a production API benchmark</small>
                </div>
              </div>
              <Card
                title="Scenario history"
                sub="Guest-scoped results; original SRE evidence remains untouched"
              >
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Run time</th>
                        <th>Scenario</th>
                        <th>Validation</th>
                        <th>Observed classification</th>
                        <th>Run time</th>
                        <th>Evidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {history.map((h) => (
                        <tr key={h.id}>
                          <td>
                            {new Date(h.created_at * 1000).toLocaleTimeString()}
                          </td>
                          <td>
                            {h.scenario_id} · {h.title}
                          </td>
                          <td>
                            <span
                              className={`pill ${h.verdict === "pass" ? "green" : "neutral"}`}
                            >
                              {h.verdict}
                            </span>
                          </td>
                          <td>{h.classifications.map(labels).join(", ")}</td>
                          <td>{milliseconds(h.duration_ms)}</td>
                          <td>
                            <button
                              className="text-btn"
                              disabled={busy}
                              onClick={() => void selectRun(h.id)}
                            >
                              Inspect <ArrowRight size={12} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {!history.length && (
                  <div className="empty">
                    No runs have been executed in this session.
                  </div>
                )}
              </Card>
            </>
          )}
          {message && (
            <div className="banner" role="status">
              <CheckCircle2 size={17} />
              {message}
            </div>
          )}
          <div className="wl-boundary">
            <ShieldCheck size={14} />
            <span>
              Offline laboratory · No live capture, device access or privileged
              network commands ·{" "}
              {caps?.guest_limits.operations_per_minute || 12} operations/minute
            </span>
          </div>
        </>
      )}
    </div>
  );
}
