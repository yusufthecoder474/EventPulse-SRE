#include "analyzer.hpp"
#include "handshake.hpp"
#include <iostream>
#include <stdexcept>
int main(int argc, char **argv) {
  try {
    long window = 5000;
    std::int64_t until = -1;
    bool handshake = false;
    for (int i = 1; i < argc; ++i) {
      std::string option = argv[i];
      if (option == "--handshakes")
        handshake = true;
      else if ((option == "--window-ms" || option == "--observed-until-us") &&
               i + 1 < argc) {
        std::string value = argv[++i];
        std::size_t used = 0;
        auto n = std::stoll(value, &used);
        if (used != value.size())
          throw std::invalid_argument("Invalid number");
        if (option == "--window-ms") {
          if (n < 500 || n > 60000)
            throw std::invalid_argument("Invalid window");
          window = static_cast<long>(n);
        } else {
          if (n < 0 || n > 9000000000000000LL)
            throw std::invalid_argument("Invalid observation end");
          until = n;
        }
      } else
        throw std::invalid_argument("Invalid arguments");
    }
    auto events = wireless::Analyzer::parse(std::cin);
    std::cout << (handshake
                      ? wireless::handshake_json(events, window * 1000, until)
                      : wireless::Analyzer(window).analyze(events).json())
              << '\n';
    return 0;
  } catch (const std::exception &) {
    std::cerr << "Invalid bounded WirelessLab event input or analysis "
                 "configuration\n";
    return 2;
  }
}
