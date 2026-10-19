#pragma once
#include <cstdint>
#include <istream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace wireless {
struct Event {
  std::string id, client, ap, kind, origin, direction, reported_state;
  std::int64_t timestamp_us = 0;
  int code = -1, sequence = -1;
  std::string replay_counter = "-1";
  int key_info = -1, descriptor_type = -1;
};
struct ClientResult {
  std::string client, ap, state = "discovered", classification = "incomplete",
                          explanation;
  bool authenticated = false, associated = false, ip_ready = false,
       dns_ready = false;
  bool auth_failed = false, assoc_failed = false, disconnected = false,
       dhcp_failed = false, dns_failed = false;
  bool missing_context = false, invalid_transition = false,
       management_inconsistent = false, management_delayed = false;
  std::int64_t association_request = -1, association_latency_us = -1,
               last_ap_change = -1, controller_lag_us = -1;
  std::set<int> eapol_messages;
  std::set<std::string> sae_commits, sae_confirms;
  std::vector<std::string> findings;
};
struct Analysis {
  std::size_t input_events = 0, processed_events = 0, duplicates = 0,
              out_of_order = 0;
  std::map<std::string, ClientResult> clients;
  std::string json() const;
};
class Analyzer {
  std::int64_t window_us_, latency_us_;

public:
  explicit Analyzer(std::int64_t window_ms = 5000,
                    std::int64_t latency_ms = 500);
  Analysis analyze(std::vector<Event> events) const;
  static std::vector<Event> parse(std::istream &input);
};
} // namespace wireless
