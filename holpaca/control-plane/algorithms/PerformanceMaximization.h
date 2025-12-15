#pragma once
#include <holpaca/control-plane/ProxyManager.h>
#include <holpaca/control-plane/algorithms/ControlAlgorithm.h>
#include <holpaca/control-plane/algorithms/Optimizable.h>
#include <holpaca/control-plane/algorithms/Spline.h>

#include <atomic>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace holpaca {

/**
 * @brief Control algorithm that optimizes cache pool sizes to maximize
 * performance.
 *
 * Uses historical metrics, QoS margins, and a utility curve to compute optimal
 * pool allocations for each cache.
 */
class PerformanceMaximization : public ControlAlgorithm {

private:
  /**
   * @brief Configuration for a single memory pool.
   *
   * Stores bounds, (current) optimal size, and the utility curve for the pool.
   */
  struct PoolConfig {
    uint64_t m_optimalSize;    /* Optimal size computed for the pool */
    uint64_t m_lowerBound{0};  /* Minimum allowed size */
    uint64_t m_upperBound{0};  /* Maximum allowed size */
    tk::spline m_utilityCurve; /* Utility curve mapping size -> performance */

    /* Compute performance metric at current optimal size */
    double getMetric() const { return m_utilityCurve(m_optimalSize); };
  };

  /**
   * @brief Configuration for a single cache, containing multiple pools.
   */
  struct CacheConfig {
    std::unordered_map<PoolId, PoolConfig>
        m_poolConfigs{}; /* Pool configurations */
  };

  /**
   * @brief Optimization context used by the algorithm.
   *
   * Inherits from Optimizable for gradient-like optimization of pool sizes.
   */
  struct Context : public Optimizable<Context> {
    std::unordered_map<std::string, CacheConfig>
        m_cacheConfigs; /* Cache configurations */

    void
    step(double const kStepSize) override final; /* Take an optimization step */
    double energy() const override final;        /* Evaluate energy (cost) */
    double distance(Optimizable const *other)
        const override final;         /* Distance to another context */
    bool skip() const override final; /* Whether to skip this step */
  };

  /* Maximum allowed change per iteration (fraction of current size) */
  double const m_kDelta{0.05};

  /* Minimum MRC length to consider a pool for optimization */
  const uint32_t m_kMRCMinLength{3};

  /* Margin applied for QoS constraints */
  double const m_kQoSMargin{0.10};

  /* FOR OVERHEAD MEASUREMENTS ONLY:
   * Whether to fake enforcement (simulate resizing without actual effect) */
  bool const m_kFakeEnforce{false};

  /* FOR OVERHEAD MEASUREMENTS ONLY:
   * Print latencies only when cache exceeds this number of entries */
  uint64_t m_printLatenciesOnEntries{0};

  /* FOR OVERHEAD MEASUREMENTS ONLY:
   * Stores latency tuples (read, write, total) for historical tracking */
  std::vector<std::tuple<std::chrono::duration<double, std::milli>,
                         std::chrono::duration<double, std::milli>,
                         std::chrono::duration<double, std::milli>>>
      m_latencies;

  /**
   * @brief Aggregated average metrics for a pool.
   */
  struct PoolAvgMetrics {
    double m_missRatio{1.0};  /* Average miss ratio */
    uint32_t m_diskIOPS{0};   /* Average disk IOPS */
    uint32_t m_throughput{0}; /* Average throughput */
  };

  /* History of pool metrics for each cache */
  std::unordered_map<std::string, std::unordered_map<PoolId, PoolAvgMetrics>>
      m_poolAvgMetricsHistory;

  /* Parameter for moving average of metrics */
  const double m_kMovingAverageParam{0.3};

  /* Main algorithm loop executed periodically */
  void loop(ProxyManager *const kProxyManager) override final;

public:
  /**
   * @brief Constructs a PerformanceMaximization algorithm instance.
   *
   * @param kProxyManager Pointer to ProxyManager for resizing pools
   * @param kPeriodicity Time between optimization iterations
   * @param kDelta Maximum allowed change per iteration
   * @param kFakeEnforce FOR OVERHEAD MEASUREMENTS ONLY:
   *    Whether to simulate resizing without enforcement
   * @param kPrintLatenciesOnEntries FOR OVERHEAD MEASUREMENTS ONLY:
   *    Threshold of entries to print latencies
   */
  PerformanceMaximization(ProxyManager *const kProxyManager,
                          std::chrono::milliseconds const kPeriodicity,
                          double const kDelta, bool const kFakeEnforce,
                          uint64_t const kPrintLatenciesOnEntries);
};

} // namespace holpaca
