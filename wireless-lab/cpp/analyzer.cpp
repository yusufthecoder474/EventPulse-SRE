#include "analyzer.hpp"
#include <algorithm>
#include <cctype>
#include <sstream>
#include <stdexcept>
#include <tuple>

namespace wireless {
namespace {
const std::set<std::string> kinds = {
    "beacon",          "probe_request", "probe_response",    "auth_request",
    "auth_ok",         "auth_fail",     "assoc_request",     "assoc_ok",
    "assoc_reject",    "deauth",        "disassoc",          "data",
    "eapol_1",         "eapol_2",       "eapol_3",           "eapol_4",
    "sae_commit",      "sae_confirm",   "dhcp_discover",     "dhcp_offer",
    "dhcp_request",    "dhcp_ack",      "dhcp_fail",         "dns_query",
    "dns_ok",          "dns_fail",      "controller_update", "client_update",
    "dashboard_update"};
bool identifier(const std::string &value) {
  return !value.empty() && value.size() <= 80 &&
         std::all_of(value.begin(), value.end(), [](unsigned char c) {
           return std::isalnum(c) || c == '_' || c == '-' || c == '.' ||
                  c == ':';
         });
}
std::int64_t number(const std::string &value, std::int64_t low,
                    std::int64_t high) {
  std::size_t used = 0;
  auto result = std::stoll(value, &used);
  if (used != value.size() || result < low || result > high)
    throw std::invalid_argument("Numeric field out of range");
  return result;
}
std::string quote(const std::string &text) {
  std::string out = "\"";
  for (unsigned char c : text) {
    if (c == '"' || c == '\\')
      out += '\\';
    if (c < 32)
      throw std::invalid_argument("Control character in output");
    out += static_cast<char>(c);
  }
  return out + '"';
}
void missing(ClientResult &c, const Event &e, const std::string &reason) {
  c.missing_context = true;
  // Packet traces may begin mid-session. Missing context is not an invalid
  // device transition.
  if (e.origin != "packet")
    c.invalid_transition = true;
  c.findings.push_back(reason);
}
void reset_connection(ClientResult &c) {
  c.authenticated = false;
  c.associated = false;
  c.ip_ready = false;
  c.dns_ready = false;
  c.auth_failed = false;
  c.assoc_failed = false;
  c.disconnected = false;
  c.dhcp_failed = false;
  c.dns_failed = false;
  c.association_request = -1;
  c.association_latency_us = -1;
  c.eapol_messages.clear();
  c.sae_commits.clear();
  c.sae_confirms.clear();
}
} // namespace
Analyzer::Analyzer(std::int64_t window_ms, std::int64_t latency_ms)
    : window_us_(window_ms * 1000), latency_us_(latency_ms * 1000) {
  if (window_ms < 1 || window_ms > 60000 || latency_ms < 1 ||
      latency_ms > window_ms)
    throw std::invalid_argument("Invalid bounded analysis window");
}
std::vector<Event> Analyzer::parse(std::istream &input) {
  std::vector<Event> events;
  std::string line;
  while (std::getline(input, line)) {
    if (!line.empty() && line.back() == '\r')
      line.pop_back();
    if (line.empty() || line.size() > 1024 || events.size() >= 50000)
      throw std::invalid_argument("Empty, oversized or excessive event record");
    std::vector<std::string> fields;
    std::istringstream row(line);
    std::string field;
    while (std::getline(row, field, '\t'))
      fields.push_back(field);
    if (fields.size() != 10 && fields.size() != 13)
      throw std::invalid_argument("Expected ten TSV fields");
    if (!identifier(fields[0]) || !identifier(fields[2]) ||
        !identifier(fields[3]) || !kinds.count(fields[4]))
      throw std::invalid_argument("Invalid event identifier or kind");
    if (fields[7] != "packet" && fields[7] != "synthetic" &&
        fields[7] != "ap" && fields[7] != "client" && fields[7] != "controller")
      throw std::invalid_argument("Invalid origin");
    if (fields[8] != "ap_to_client" && fields[8] != "client_to_ap" &&
        fields[8] != "unknown")
      throw std::invalid_argument("Invalid direction");
    if (fields[9] != "unknown" && fields[9] != "connected" &&
        fields[9] != "disconnected")
      throw std::invalid_argument("Invalid controller state");
    events.push_back({fields[0], fields[2], fields[3], fields[4], fields[7],
                      fields[8], fields[9],
                      number(fields[1], 0, 9000000000000000LL),
                      static_cast<int>(number(fields[5], -1, 65535)),
                      static_cast<int>(number(fields[6], -1, 65535))});
    if (fields.size() == 13) {
      if (fields[10] != "-1") {
        if (fields[10].empty() || fields[10].size() > 20 ||
            !std::all_of(fields[10].begin(), fields[10].end(),
                         [](unsigned char c) { return c >= '0' && c <= '9'; }))
          throw std::invalid_argument("Invalid replay counter");
        std::size_t used = 0;
        std::stoull(fields[10], &used);
        if (used != fields[10].size())
          throw std::invalid_argument("Invalid replay counter");
      }
      events.back().replay_counter = fields[10];
      events.back().key_info = static_cast<int>(number(fields[11], -1, 65535));
      events.back().descriptor_type =
          static_cast<int>(number(fields[12], -1, 255));
    }
  }
  return events;
}
Analysis Analyzer::analyze(std::vector<Event> events) const {
  Analysis result;
  result.input_events = events.size();
  for (std::size_t i = 1; i < events.size(); ++i)
    if (events[i].timestamp_us < events[i - 1].timestamp_us)
      ++result.out_of_order;
  std::stable_sort(events.begin(), events.end(),
                   [](const Event &a, const Event &b) {
                     return a.timestamp_us < b.timestamp_us;
                   });
  std::set<std::tuple<std::int64_t, std::string, std::string, std::string, int,
                      int, std::string, std::string, std::string>>
      seen;
  for (const auto &e : events) {
    auto key =
        std::make_tuple(e.timestamp_us, e.client, e.ap, e.kind, e.code,
                        e.sequence, e.origin, e.direction, e.reported_state);
    if (!seen.insert(key).second) {
      ++result.duplicates;
      continue;
    }
    ++result.processed_events;
    if (e.client == "broadcast" || e.client == "unknown_client" ||
        e.kind == "beacon" || e.kind == "probe_request" ||
        e.kind == "probe_response")
      continue;
    // A client can join multiple APs; state is scoped to the client/AP pair.
    auto &c = result.clients[e.client + "@" + e.ap];
    c.client = e.client;
    c.ap = e.ap;
    const auto &k = e.kind;
    if (k == "auth_request") {
      reset_connection(c);
      c.state = "authenticating";
    } else if (k == "auth_ok") {
      c.authenticated = true;
      c.auth_failed = false;
      c.state = "authenticated";
    } else if (k == "auth_fail") {
      c.auth_failed = true;
      c.state = "authentication_failed";
      c.findings.push_back("Authentication rejection is explicit; password "
                           "cause is not established.");
    } else if (k == "sae_commit") {
      c.sae_commits.insert(e.direction);
      c.state = "sae_observed";
    } else if (k == "sae_confirm") {
      c.sae_confirms.insert(e.direction);
      if (c.sae_commits.count("ap_to_client") &&
          c.sae_commits.count("client_to_ap") &&
          c.sae_confirms.count("ap_to_client") &&
          c.sae_confirms.count("client_to_ap")) {
        c.authenticated = true;
        c.state = "authenticated";
      }
    } else if (k == "assoc_request") {
      c.association_request = e.timestamp_us;
      if (!c.authenticated)
        missing(
            c, e,
            "Association request has no preceding authentication evidence.");
      c.state = "associating";
    } else if (k == "assoc_reject") {
      c.assoc_failed = true;
      c.state = "association_failed";
      c.findings.push_back(
          "AP association response contains an explicit nonzero status.");
    } else if (k == "assoc_ok") {
      if (c.association_request < 0 ||
          e.timestamp_us - c.association_request > window_us_) {
        missing(
            c, e,
            "No association request within the configured correlation window.");
      } else
        c.association_latency_us = e.timestamp_us - c.association_request;
      c.associated = true;
      c.disconnected = false;
      c.state = "associated";
      c.last_ap_change = e.timestamp_us;
    } else if (k == "deauth" || k == "disassoc") {
      c.associated = false;
      c.ip_ready = false;
      c.dns_ready = false;
      c.disconnected = true;
      c.state = "disconnected";
      c.last_ap_change = e.timestamp_us;
      c.findings.push_back("Explicit disconnect/reason evidence observed; root "
                           "cause beyond the code remains unproven.");
    } else if (k.rfind("eapol_", 0) == 0) {
      int message = k.back() - '0';
      c.eapol_messages.insert(message);
      if (!c.associated)
        missing(c, e,
                "EAPOL is present without radio association context; Ethernet "
                "EAPOL alone is insufficient.");
    } else if (k == "dhcp_ack") {
      if (!c.associated)
        missing(c, e,
                "IP configuration is observed without association evidence.");
      c.ip_ready = true;
      c.dhcp_failed = false;
      c.state = "ip_ready";
    } else if (k == "dhcp_fail") {
      c.dhcp_failed = true;
      c.state = "dhcp_failed";
      c.findings.push_back("Explicit DHCP NAK or synthetic timeout evidence; "
                           "association is a separate layer.");
    } else if (k == "dns_ok") {
      c.dns_ready = true;
      c.state = "online";
    } else if (k == "dns_fail") {
      c.dns_failed = true;
      c.state = "dns_failed";
      c.findings.push_back("DNS error response or explicit synthetic failure "
                           "observed; this is not an RF failure.");
    } else if (k == "controller_update") {
      if (c.last_ap_change >= 0) {
        c.controller_lag_us = e.timestamp_us - c.last_ap_change;
        if (c.controller_lag_us > window_us_) {
          c.management_delayed = true;
          c.findings.push_back(
              "Controller observation arrived after the correlation window; "
              "timestamps assume a shared clock.");
        }
        bool expected = c.associated;
        if ((e.reported_state == "connected" && !expected) ||
            (e.reported_state == "disconnected" && expected)) {
          c.management_inconsistent = true;
          c.findings.push_back(
              "Controller status disagrees with the latest explicit AP state.");
        }
      } else {
        c.missing_context = true;
        c.findings.push_back(
            "Controller update has no AP state for comparison.");
      }
    }
  }
  for (auto &entry : result.clients) {
    auto &c = entry.second;
    if (c.management_inconsistent) {
      c.classification = "management_inconsistent";
      c.explanation = "AP/controller disagreement is demonstrated, not a Cisco "
                      "controller fault.";
    } else if (c.auth_failed) {
      c.classification = "authentication_failed";
      c.explanation = "Explicit authentication rejection observed; credentials "
                      "are not inspected.";
    } else if (c.assoc_failed) {
      c.classification = "association_rejected";
      c.explanation = "Explicit AP association rejection observed.";
    } else if (c.disconnected) {
      c.classification = "disconnected";
      c.explanation =
          "Explicit deauthentication/disassociation evidence observed.";
    } else if (c.dhcp_failed) {
      c.classification = "dhcp_failed";
      c.explanation = "IP allocation failure is explicit; Wi-Fi joining and "
                      "DHCP are distinct.";
    } else if (c.dns_failed) {
      c.classification = "dns_failed";
      c.explanation = "DNS failure is explicit; it does not establish a "
                      "wireless association failure.";
    } else if (c.management_delayed) {
      c.classification = "management_delayed";
      c.explanation =
          "Controller update exceeds the configured event-correlation window.";
    } else if (c.missing_context || !c.associated) {
      c.classification = "incomplete";
      c.explanation = "Capture/events do not establish the complete connection "
                      "path; no missing failure cause is invented.";
    } else if (c.association_latency_us > latency_us_) {
      c.classification = "association_delayed";
      c.explanation = "Matched request/response exceeds the local laboratory "
                      "latency threshold.";
    } else {
      c.classification = "association_success";
      c.explanation =
          "Authentication and successful association evidence observed; IP "
          "access and cryptographic validity are separate.";
    }
  }
  return result;
}
std::string Analysis::json() const {
  std::ostringstream out;
  out << "{\"schema_version\":1,\"engine\":\"C++17\",\"input_events\":"
      << input_events << ",\"processed_events\":" << processed_events
      << ",\"duplicate_events\":" << duplicates
      << ",\"out_of_order_pairs\":" << out_of_order << ",\"clients\":[";
  bool first = true;
  for (const auto &entry : clients) {
    const auto &c = entry.second;
    if (!first)
      out << ',';
    first = false;
    out << "{\"client\":" << quote(c.client) << ",\"ap\":" << quote(c.ap)
        << ",\"state\":" << quote(c.state)
        << ",\"classification\":" << quote(c.classification)
        << ",\"explanation\":" << quote(c.explanation)
        << ",\"association_latency_ms\":";
    if (c.association_latency_us < 0)
      out << "null";
    else
      out << static_cast<double>(c.association_latency_us) / 1000;
    out << ",\"controller_lag_ms\":";
    if (c.controller_lag_us < 0)
      out << "null";
    else
      out << static_cast<double>(c.controller_lag_us) / 1000;
    out << ",\"invalid_transition\":"
        << (c.invalid_transition ? "true" : "false")
        << ",\"eapol_messages_observed\":[";
    bool initial = true;
    for (int n : c.eapol_messages) {
      if (!initial)
        out << ',';
      initial = false;
      out << n;
    }
    out << "],\"key_exchange\":"
        << quote(c.eapol_messages.size() == 4
                     ? "four_messages_observed_not_cryptographically_verified"
                     : "incomplete_or_not_captured")
        << ",\"sae_exchange\":"
        << quote(c.sae_commits.count("ap_to_client") &&
                         c.sae_commits.count("client_to_ap") &&
                         c.sae_confirms.count("ap_to_client") &&
                         c.sae_confirms.count("client_to_ap")
                     ? "bidirectional_events_observed_not_crypto_verified"
                     : "incomplete_or_not_captured")
        << ",\"findings\":[";
    initial = true;
    for (const auto &finding : c.findings) {
      if (!initial)
        out << ',';
      initial = false;
      out << quote(finding);
    }
    out << "]}";
  }
  return out.str() + "]}";
}
} // namespace wireless
