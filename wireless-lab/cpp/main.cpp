#include "analyzer.hpp"
#include <iostream>
#include <stdexcept>
int main(int argc, char **argv) {
  try {
    long window = 5000;
    if (argc == 3 && std::string(argv[1]) == "--window-ms") {
      std::size_t used = 0;
      window = std::stol(argv[2], &used);
      if (used != std::string(argv[2]).size())
        throw std::invalid_argument("Invalid window");
    } else if (argc != 1)
      throw std::invalid_argument(
          "Usage: wireless_analyzer [--window-ms 5000]");
    wireless::Analyzer analyzer(window);
    std::cout << analyzer.analyze(wireless::Analyzer::parse(std::cin)).json()
              << '\n';
    return 0;
  } catch (const std::exception &) {
    std::cerr << "Invalid bounded WirelessLab event input or analysis "
                 "configuration\n";
    return 2;
  }
}
