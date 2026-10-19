#include "handshake.hpp"
#include <algorithm>
#include <iostream>
#include <sstream>
#include <stdexcept>
using wireless::Event;
Event packet(int n, long t, const std::string &client = "clientA",
             int base = 10) {
  Event e;
  e.id = client + "_" + std::to_string(n) + "_" + std::to_string(t);
  e.client = client;
  e.ap = "apA";
  e.kind = "eapol_" + std::to_string(n);
  e.timestamp_us = t;
  e.origin = "synthetic";
  e.direction = (n == 1 || n == 3) ? "ap_to_client" : "client_to_ap";
  e.replay_counter = std::to_string(base + (n >= 3));
  e.key_info = (n == 1 ? 138 : n == 2 ? 266 : n == 3 ? 970 : 778);
  e.descriptor_type = 2;
  return e;
}
void require(bool x) {
  if (!x)
    throw std::runtime_error("Assertion failed");
}
std::string analyze(const std::vector<Event> &v, long until = -1) {
  return wireless::handshake_json(v, 5000000, until);
}
void classification(const std::vector<Event> &v, const std::string &expected,
                    long until = -1) {
  require(analyze(v, until).find("\"classification\":\"" + expected + "\"") !=
          std::string::npos);
}
int main(int argc, char **argv) {
  try {
    require(argc == 2);
    std::string name = argv[1];
    std::vector<Event> v = {packet(1, 100000), packet(2, 200000),
                            packet(3, 300000), packet(4, 400000)};
    if (name == "complete")
      classification(v, "HANDSHAKE_COMPLETE");
    else if (name.rfind("missing", 0) == 0) {
      v.erase(v.begin() + name.back() - '1');
      classification(v, "HANDSHAKE_INCOMPLETE");
    } else if (name == "reordered") {
      v[1].timestamp_us = 350000;
      classification(v, "UNEXPECTED_SEQUENCE");
    } else if (name == "retransmitted" || name == "duplicate") {
      v.push_back(packet(2, 250000));
      classification(v, "HANDSHAKE_COMPLETE");
      require(analyze(v).find("\"possible_retransmissions\":1") !=
              std::string::npos);
    } else if (name == "timeout") {
      v.resize(2);
      classification(v, "HANDSHAKE_TIMEOUT", 6000000);
    } else if (name == "incomplete") {
      v.resize(1);
      v[0].replay_counter = "-1";
      classification(v, "INSUFFICIENT_EVIDENCE");
    } else if (name == "concurrent") {
      for (int i = 1; i <= 4; ++i)
        v.push_back(packet(i, i * 100000, "clientB", 30));
      auto s = analyze(v);
      require(s.find("hs_2") != std::string::npos &&
              s.find("INCOMPLETE") == std::string::npos);
    } else if (name == "malformed_metadata") {
      v[1].key_info = 0;
      classification(v, "INSUFFICIENT_EVIDENCE");
      std::istringstream input(
          "e\t1\tc\ta\teapol_1\t0\t0\tpacket\tap_to_"
          "client\tunknown\t18446744073709551616\t138\t2\n");
      bool rejected = false;
      try {
        wireless::Analyzer::parse(input);
      } catch (const std::exception &) {
        rejected = true;
      }
      require(rejected);
    } else if (name == "ambiguous") {
      v = {packet(1, 100000, "clientA", 10), packet(1, 150000, "clientA", 20),
           packet(3, 200000, "clientA", 30)};
      classification(v, "INSUFFICIENT_EVIDENCE");
    } else if (name == "boundary") {
      v[0].replay_counter = v[1].replay_counter = "18446744073709551614";
      v[2].replay_counter = v[3].replay_counter = "18446744073709551615";
      classification(v, "HANDSHAKE_COMPLETE");
    } else if (name == "empty")
      require(analyze({}).find("\"sessions\":[]") != std::string::npos);
    else if (name == "timestamp") {
      std::reverse(v.begin(), v.end());
      classification(v, "HANDSHAKE_COMPLETE");
      require(analyze(v) == analyze(v));
    } else if (name == "bounded_large") {
      v.clear();
      for (int c = 0; c < 2500; ++c)
        for (int n = 1; n <= 4; ++n)
          v.push_back(packet(n, n * 100000, "client" + std::to_string(c)));
      auto result = analyze(v);
      require(result.find("hs_2500") != std::string::npos);
    } else if (name == "replay_mismatch") {
      v[3].replay_counter = "20";
      require(analyze(v).find("HANDSHAKE_COMPLETE") == std::string::npos);
    } else
      throw std::runtime_error("Unknown test");
    std::cout << "PASS " << name << '\n';
    return 0;
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
