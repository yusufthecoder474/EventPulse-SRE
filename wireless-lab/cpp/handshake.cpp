#include "handshake.hpp"
#include <algorithm>
#include <array>
#include <limits>
#include <sstream>
#include <stdexcept>
namespace wireless {
namespace {
struct Session {
  std::string client, ap;
  std::int64_t first = 0, last = 0;
  std::array<bool, 5> seen{};
  std::array<std::string, 5> counters{};
  std::vector<Event> refs;
  int highest = 0, retries = 0;
  bool insufficient = false, unexpected = false;
};
bool known(const std::string &s) {
  return s.rfind("unknown", 0) != 0 && s != "broadcast";
}
std::uint64_t counter(const Event &e) { return std::stoull(e.replay_counter); }
bool metadata(const Event &e, int m) {
  if (e.replay_counter == "-1" || !known(e.client) || !known(e.ap) ||
      e.descriptor_type != 2 || e.key_info < 0 || (e.key_info & 7) != 2 ||
      !(e.key_info & 8) || (e.key_info & 0xc00))
    return false;
  const bool ack = e.key_info & 0x80, mic = e.key_info & 0x100,
             install = e.key_info & 0x40, secure = e.key_info & 0x200;
  if (e.direction != ((m == 1 || m == 3) ? "ap_to_client" : "client_to_ap"))
    return false;
  return (m == 1 && ack && !mic && !install && !secure) ||
         (m == 2 && !ack && mic && !install && !secure) ||
         (m == 3 && ack && mic && install) ||
         (m == 4 && !ack && mic && !install && secure);
}
std::string quote(const std::string &s) {
  std::string out = "\"";
  for (char c : s) {
    if (c == '"' || c == '\\')
      out += '\\';
    if (static_cast<unsigned char>(c) < 32)
      throw std::invalid_argument("Unsafe output");
    out += c;
  }
  return out + '"';
}
} // namespace
std::string handshake_json(std::vector<Event> events, std::int64_t window_us,
                           std::int64_t observed_until_us) {
  if (events.size() > 50000 || window_us < 500000 || window_us > 60000000 ||
      observed_until_us > 9000000000000000LL)
    throw std::invalid_argument("Invalid handshake bounds");
  std::stable_sort(events.begin(), events.end(),
                   [](const Event &a, const Event &b) {
                     return a.timestamp_us < b.timestamp_us;
                   });
  std::vector<Session> sessions;
  std::map<std::pair<std::string, std::string>, std::vector<std::size_t>>
      active;
  if (!events.empty())
    observed_until_us = std::max(observed_until_us, events.back().timestamp_us);
  for (const auto &e : events) {
    if (e.kind.rfind("eapol_", 0) != 0)
      continue;
    const int m = e.kind.back() - '0';
    if (m < 1 || m > 4)
      continue;
    std::vector<std::size_t> candidates;
    // Distinct M1 replay counters create distinct attempts. Multiple matching
    // attempts remain ambiguous.
    auto &pair_sessions = active[{e.client, e.ap}];
    pair_sessions.erase(
        std::remove_if(pair_sessions.begin(), pair_sessions.end(),
                       [&](std::size_t i) {
                         return e.timestamp_us - sessions[i].first > window_us;
                       }),
        pair_sessions.end());
    for (const auto i : pair_sessions) {
      auto &s = sessions[i];
      if (s.client != e.client || s.ap != e.ap ||
          e.timestamp_us - s.first > window_us)
        continue;
      if (e.replay_counter == "-1")
        continue;
      if (m <= 2) {
        const auto &r = s.counters[1].empty() ? s.counters[2] : s.counters[1];
        if (r == e.replay_counter)
          candidates.push_back(i);
      } else if (!s.counters[m].empty() && s.counters[m] == e.replay_counter)
        candidates.push_back(i);
      else if (!s.counters[3].empty() && m == 4 &&
               s.counters[3] == e.replay_counter)
        candidates.push_back(i);
      else if (s.counters[3].empty() && !s.counters[1].empty() &&
               counter(e) > std::stoull(s.counters[1]))
        candidates.push_back(i);
      else if (s.counters[3].empty() && s.counters[1].empty() &&
               !s.counters[2].empty() &&
               counter(e) > std::stoull(s.counters[2]))
        candidates.push_back(i);
    }
    std::size_t selected = 0;
    if (candidates.size() == 1)
      selected = candidates[0];
    else {
      for (auto index : candidates)
        sessions[index].insufficient = true;
      Session s;
      s.client = e.client;
      s.ap = e.ap;
      s.first = e.timestamp_us;
      s.last = e.timestamp_us;
      s.insufficient = candidates.size() > 1;
      if (pair_sessions.size() >= 64)
        throw std::invalid_argument(
            "Too many simultaneous attempts for one client/authenticator");
      sessions.push_back(s);
      selected = sessions.size() - 1;
      pair_sessions.push_back(selected);
    }
    auto &s = sessions[selected];
    s.last = e.timestamp_us;
    if (!metadata(e, m))
      s.insufficient = true;
    if (s.seen[m]) {
      if (s.counters[m] == e.replay_counter)
        ++s.retries;
      else
        s.insufficient = true;
    } else {
      if (m < s.highest)
        s.unexpected = true;
      s.highest = std::max(s.highest, m);
      s.seen[m] = true;
      s.counters[m] = e.replay_counter;
    }
    s.refs.push_back(e);
  }
  std::ostringstream out;
  out << "{\"engine\":\"C++17\",\"schema_version\":1,\"cryptographically_"
         "verified\":false,\"sessions\":[";
  for (std::size_t i = 0; i < sessions.size(); ++i) {
    const auto &s = sessions[i];
    if (i)
      out << ',';
    bool complete = s.seen[1] && s.seen[2] && s.seen[3] && s.seen[4];
    bool counters_ok =
        !complete ||
        (s.counters[1] == s.counters[2] && s.counters[3] == s.counters[4] &&
         std::stoull(s.counters[3]) > std::stoull(s.counters[1]));
    std::string classification = "HANDSHAKE_INCOMPLETE",
                reason = "Missing messages indicate incomplete observed "
                         "evidence, not a proven authentication failure.";
    if (s.insufficient || !counters_ok) {
      classification = "INSUFFICIENT_EVIDENCE";
      reason = "Missing, unsupported or ambiguous roles, key flags, descriptor "
               "or replay-counter correlation.";
    } else if (s.unexpected) {
      classification = "UNEXPECTED_SEQUENCE";
      reason = "A previously unseen earlier stage follows a later stage in "
               "timestamp order.";
    } else if (complete) {
      classification = "HANDSHAKE_COMPLETE";
      reason =
          "Four ordered, role/flag/replay-consistent message observations; no "
          "MIC, key installation or password verification.";
    } else if (observed_until_us - s.first >= window_us) {
      classification = "HANDSHAKE_TIMEOUT";
      reason =
          "Observed capture interval extends past the configured completion "
          "window; this is not proof of the device's internal timeout.";
    }
    out << "{\"session_id\":\"hs_" << i + 1
        << "\",\"client\":" << quote(s.client)
        << ",\"authenticator\":" << quote(s.ap)
        << ",\"classification\":" << quote(classification)
        << ",\"explanation\":" << quote(reason)
        << ",\"possible_retransmissions\":" << s.retries
        << ",\"missing_messages\":[";
    bool comma = false;
    for (int m = 1; m <= 4; ++m)
      if (!s.seen[m]) {
        if (comma)
          out << ',';
        out << m;
        comma = true;
      }
    out << "],\"packet_references\":[";
    for (std::size_t n = 0; n < s.refs.size(); ++n) {
      const auto &e = s.refs[n];
      if (n)
        out << ',';
      out << "{\"event_id\":" << quote(e.id)
          << ",\"timestamp_us\":" << e.timestamp_us
          << ",\"message\":" << e.kind.back()
          << ",\"replay_counter\":" << quote(e.replay_counter)
          << ",\"direction\":" << quote(e.direction) << "}";
    }
    out << "]}";
  }
  out << "],\"limitations\":[\"WPA2-Personal-style descriptor-2, pairwise CCMP "
         "key-version-2 observations only; security policy is not proven "
         "without RSN context.\",\"Retransmissions are metadata-consistent "
         "candidates, not byte-for-byte payload verification.\",\"Concurrent "
         "attempts with insufficient identifiers are ambiguous; no WPA3 or "
         "cryptographic validation.\"]}";
  return out.str();
}
} // namespace wireless
