import {
  render,
  screen,
  waitFor,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { afterEach, describe, it, expect, vi } from "vitest";
import App from "./App";
import { pct, ms } from "./types";
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});
describe("console states", () => {
  it("renders loading and then actionable API failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Connecting");
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("offline"),
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
  it("renders real empty states and all navigation destinations", async () => {
    const s = {
      history: [],
      endpoints: [],
      histogram: [],
      window_seconds: 60,
      version: "1.0.0",
      uptime: 12,
      database_ready: true,
      active_incidents: 0,
      faults_enabled: false,
      fault: "none",
      status: "no traffic",
      requests: 0,
      errors: 0,
      rps: 0,
      availability: null,
      p95: null,
      p50: null,
      p99: null,
      error_rate: null,
      budget_remaining: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        json: async () =>
          url.includes("summary")
            ? s
            : url.includes("incidents")
              ? []
              : { runs: [], summary: {}, source: "No experiments" },
      })),
    );
    render(<App />);
    await waitFor(() =>
      expect(screen.getByText("NO TRAFFIC")).toBeInTheDocument(),
    );
    expect(screen.getByText(/No business requests/)).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Fault injection lab" }),
    );
    expect(screen.getByText(/Fault injection is disabled/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /HTTP 500 burst/ }),
    ).toBeDisabled();
  });
  it("formats missing values without inventing health", () => {
    expect(pct(null)).toBe("—");
    expect(ms(undefined)).toBe("—");
    expect(pct(0.99)).toBe("99.00%");
    expect(ms(0.5)).toBe("500.0 ms");
  });
});
