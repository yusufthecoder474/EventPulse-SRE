#include "analyzer.hpp"
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
using wireless::Event;
Event event(const std::string &kind, long time, int code = 0) {
  return {kind + std::to_string(time),
          "client1",
          "ap1",
          kind,
          "synthetic",
          "ap_to_client",
          "unknown",
          time,
          code,
          1};
}
void require(bool test) {
  if (!test)
    throw std::runtime_error("Assertion failed");
}
std::vector<Event> associated() {
  return {event("auth_ok", 0), event("assoc_request", 1000),
          event("assoc_ok", 100000)};
}
int main(int argc, char **argv) {
  try {
    if (argc != 2)
      throw std::runtime_error("Test case required");
    std::string test = argv[1];
    wireless::Analyzer engine;
    auto data = associated();
    if (test == "success")
      require(engine.analyze(data).clients.begin()->second.classification ==
              "association_success");
    else if (test == "reject") {
      data.back() = event("assoc_reject", 100000, 17);
      require(engine.analyze(data).clients.begin()->second.classification ==
              "association_rejected");
    } else if (test == "auth_failure")
      require(engine.analyze({event("auth_fail", 1, 13)})
                  .clients.begin()
                  ->second.classification == "authentication_failed");
    else if (test == "disconnect") {
      data.push_back(event("deauth", 200000, 3));
      require(engine.analyze(data).clients.begin()->second.classification ==
              "disconnected");
    } else if (test == "dhcp") {
      data.push_back(event("dhcp_fail", 200000));
      require(engine.analyze(data).clients.begin()->second.classification ==
              "dhcp_failed");
    } else if (test == "dns") {
      data.push_back(event("dhcp_ack", 200000));
      data.push_back(event("dns_fail", 300000));
      require(engine.analyze(data).clients.begin()->second.classification ==
              "dns_failed");
    } else if (test == "delayed") {
      data.back().timestamp_us = 1000000;
      require(engine.analyze(data).clients.begin()->second.classification ==
              "association_delayed");
    } else if (test == "window") {
      data.back().timestamp_us = 6000000;
      require(engine.analyze(data).clients.begin()->second.classification ==
              "incomplete");
    } else if (test == "duplicate") {
      data.push_back(data.back());
      require(engine.analyze(data).duplicates == 1);
    } else if (test == "out_of_order") {
      std::swap(data[0], data[2]);
      auto result = engine.analyze(data);
      require(result.out_of_order > 0 &&
              result.clients.begin()->second.classification ==
                  "association_success");
    } else if (test == "empty") {
      std::istringstream in("");
      require(engine.analyze(engine.parse(in)).clients.empty());
    } else if (test == "malformed") {
      bool rejected = false;
      try {
        std::istringstream in("broken\n");
        engine.parse(in);
      } catch (const std::exception &) {
        rejected = true;
      }
      require(rejected);
    } else if (test == "numeric") {
      bool rejected = false;
      try {
        std::istringstream in("id\tNaN\tsta\tap\tauth_ok\t0\t1\tsynthetic\tap_"
                              "to_client\tunknown\n");
        engine.parse(in);
      } catch (const std::exception &) {
        rejected = true;
      }
      require(rejected);
    } else if (test == "deterministic")
      require(engine.analyze(data).json() == engine.analyze(data).json());
    else if (test == "management") {
      auto update = event("controller_update", 8000000);
      update.origin = "controller";
      update.reported_state = "disconnected";
      data.push_back(update);
      auto c = engine.analyze(data).clients.begin()->second;
      require(c.management_delayed && c.management_inconsistent);
    } else if (test == "ethernet_eapol") {
      auto e = event("eapol_1", 1);
      e.origin = "packet";
      auto c = engine.analyze({e}).clients.begin()->second;
      require(c.classification == "incomplete" && !c.invalid_transition);
    } else if (test == "invalid_transition") {
      auto c = engine.analyze({event("dhcp_ack", 1)}).clients.begin()->second;
      require(c.invalid_transition && c.classification == "incomplete");
    } else if (test == "key_exchange") {
      for (int n = 1; n <= 4; ++n)
        data.push_back(event("eapol_" + std::to_string(n), 100000 + n));
      require(
          engine.analyze(data).clients.begin()->second.eapol_messages.size() ==
          4);
    } else if (test == "sae") {
      data.clear();
      for (const auto &kind : {"sae_commit", "sae_confirm"})
        for (const auto &direction : {"client_to_ap", "ap_to_client"}) {
          auto e = event(kind, static_cast<long>(data.size()) + 1);
          e.direction = direction;
          data.push_back(e);
        }
      require(engine.analyze(data).clients.begin()->second.authenticated);
    } else if (test == "multiple_clients") {
      auto other = event("auth_fail", 1, 13);
      other.client = "client2";
      data.push_back(other);
      require(engine.analyze(data).clients.size() == 2);
    } else if (test == "reconnect") {
      data.push_back(event("deauth", 200000));
      data.push_back(event("auth_request", 300000));
      data.push_back(event("auth_ok", 400000));
      data.push_back(event("assoc_request", 500000));
      data.push_back(event("assoc_ok", 600000));
      require(engine.analyze(data).clients.begin()->second.classification ==
              "association_success");
    } else
      throw std::runtime_error("Unknown test");
    std::cout << "PASS " << test << '\n';
    return 0;
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }
}
