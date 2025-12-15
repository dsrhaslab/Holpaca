#pragma once

#include <holpaca/control-plane/ProxyManager.h>

#include <atomic>
#include <chrono>
#include <thread>
#include <unordered_map>

namespace holpaca {

/**
 * @brief Base class for all control algorithms in the Holpaca system.
 *
 * This class handles periodic execution of the algorithm's main loop
 * in a separate thread and provides access to the ProxyManager for
 * interacting with caches.
 */
class ControlAlgorithm {
  /* Period between consecutive loop executions */
  std::chrono::milliseconds const m_kPeriodicity;

  /* Flag to signal the thread to stop */
  std::atomic_bool m_stop{false};

  /* Background thread running the loop periodically */
  std::thread m_thread;

  /* Pointer to the ProxyManager used to query and resize caches */
  ProxyManager *const m_kProxyManager;

protected:
  /**
   * @brief Main loop of the algorithm, executed periodically.
   *
   * Derived classes must implement this function to define
   * their specific control logic.
   *
   * @param kProxyManager ProxyManager used to interact with caches
   */
  virtual void loop(ProxyManager *const kProxyManager) = 0;

public:
  /**
   * @brief Constructs a ControlAlgorithm instance and starts its background
   * thread.
   *
   * @param kProxyManager Pointer to the ProxyManager managing caches
   * @param kPeriodicity Time interval between consecutive loop executions
   */
  ControlAlgorithm(ProxyManager *const kProxyManager,
                   std::chrono::milliseconds const kPeriodicity)
      : m_kProxyManager(kProxyManager), m_kPeriodicity(kPeriodicity) {
    m_thread = std::thread([this]() {
      while (!m_stop) {
        loop(m_kProxyManager);
        std::this_thread::sleep_for(m_kPeriodicity);
      }
    });
  }

  /**
   * @brief Stops the background thread and cleans up resources.
   *
   * Signals the thread to stop and joins it if still running.
   */
  ~ControlAlgorithm() {
    m_stop = true;
    if (m_thread.joinable()) {
      m_thread.join();
    }
  }
};

} // namespace holpaca
