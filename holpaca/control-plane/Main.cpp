#include <holpaca/control-plane/Orchestrator.h>
#include <holpaca/control-plane/algorithms/ControlAlgorithm.h>
#include <holpaca/control-plane/algorithms/Motivation.h>
#include <holpaca/control-plane/algorithms/PerformanceMaximization.h>

#include <chrono>
#include <iostream>
#include <sstream>
#include <thread>

using namespace ::holpaca;

/**
 * @brief Splits a string by the specified delimiter.
 *
 * @param str Input string to split
 * @param delimiter Character used to separate tokens
 * @return Vector of tokens
 */
std::vector<std::string> split(const std::string &str, char delimiter) {
  std::vector<std::string> tokens;
  std::string token;
  std::istringstream tokenStream(str);
  while (std::getline(tokenStream, token, delimiter)) {
    tokens.push_back(token);
  }
  return tokens;
}

/**
 * @brief Entry point of the control-plane orchestrator program.
 *
 * Parses command-line arguments, starts the Orchestrator, and installs
 * optional control algorithms.
 *
 * @param argc Argument count
 * @param argv Argument values
 * @return Exit code (0 = success, 1 = error)
 */
int main(int argc, char **argv) {
  // Display help if not enough arguments
  if (argc < 2) {
    std::cerr
        << "NAME\n"
        << "  " << argv[0]
        << " - run with specified cache settings and control algorithms\n\n"

        << "SYNOPSIS\n"
        << "  " << argv[0]
        << " <address> "
           "[<control-algorithm> <arg0:arg1:...:argn>]...\n\n"

        << "DESCRIPTION\n"
        << "  Launches the program using the given address.\n"
        << "  Optionally, one or more control algorithms may be specified, "
           "each followed by\n"
        << "  a colon-separated list of arguments.\n\n"

        << "OPTIONS\n"
        << "  <address>\n"
        << "      The IP address or hostname for the Orchestrator to bind "
           "to.\n\n"

        << "  <control-algorithm>\n"
        << "      (Optional) Name of a control algorithm module to run.\n\n"

        << "  <arg0:arg1:...:argn>\n"
        << "      (Optional) Colon-separated arguments passed to the control "
           "algorithm.\n\n"

        << "EXAMPLES\n"
        << "  " << argv[0]
        << " localhost:11110 ThroughputMaximization 1000:0.01\n\n"

        << std::endl;

    return 1;
  }

  // Start the orchestrator server
  Orchestrator orchestrator(argv[1]);

  // Parse control algorithm arguments if any
  for (int i = 2; i < argc; i += 2) {
    if (i + 1 >= argc) {
      std::cerr << "Control algorithm requires at least 1 argument: "
                   "<control-algorithm> <arg0:arg1:...:argn>"
                << std::endl;
      return 1;
    }

    auto args = split(argv[i + 1], ':');

    // ThroughputMaximization algorithm
    if (std::string(argv[i]) == "ThroughputMaximization") {
      if (args.size() < 2) {
        std::cerr
            << "ThroughputMaximization requires 2 arguments: <periodicity "
               "(ms)> "
               "<max delta ([0,1])> [fake enforce?] "
               "[print latencies on #entries]"
            << std::endl;
        return 1;
      }

      orchestrator.addAlgorithm<PerformanceMaximization>(
          std::chrono::milliseconds(std::stoul(args[0])), std::stod(args[1]),
          args.size() > 2 && args[2] == "true",
          std::stol(args.size() > 3 ? args[3] : "0"));

      // Motivation algorithm
    } else if (std::string(argv[i]) == "Motivation") {
      if (args.size() < 1) {
        std::cerr << "Motivation requires 1 argument: <periodicity (ms)>"
                  << std::endl;
        return 1;
      }

      orchestrator.addAlgorithm<Motivation>(
          std::chrono::milliseconds(std::stoul(args[0])));

    } else {
      std::cerr << "Unknown control algorithm: " << argv[i] << std::endl;
      return 1;
    }
  }

  // Keep the program running indefinitely
  while (true) {
    std::this_thread::sleep_for(std::chrono::seconds(10));
  }

  return 0;
}
