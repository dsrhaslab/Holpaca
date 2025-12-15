#pragma once
#include <holpaca/control-plane/algorithms/ControlAlgorithm.h>
#include <unordered_set>

namespace holpaca {

/**
 * @brief Motivation control algorithm.
 *
 * This algorithm allocates cache pool sizes based on predefined proportions.
 *
 */
class Motivation : public ControlAlgorithm {

  /**
   * @brief Main loop executed periodically by the algorithm.
   *
   * This function is called by the ControlAlgorithm base class and
   * interacts with the ProxyManager to observe or adjust cache pools.
   *
   * @param kProxyManager ProxyManager used to query or modify caches
   */
  void loop(ProxyManager *const kProxyManager) override final;

public:
  /**
   * @brief Constructs a Motivation algorithm instance.
   *
   * @param kProxyManager Pointer to the ProxyManager managing caches
   * @param kPeriodicity Periodicity of loop execution
   */
  Motivation(ProxyManager *const kProxyManager,
             std::chrono::milliseconds const kPeriodicity);
};

} // namespace holpaca
