#pragma once
#include "analyzer.hpp"
namespace wireless {
// Observation classification only. No nonce, key or MIC material is consumed.
std::string handshake_json(std::vector<Event> events, std::int64_t window_us,
                           std::int64_t observed_until_us = -1);
} // namespace wireless
