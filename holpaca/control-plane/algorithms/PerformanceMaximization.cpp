#include <holpaca/control-plane/algorithms/PerformanceMaximization.h>

#include <cmath>
#include <istream>
#include <numeric>

namespace holpaca {

/**
 * @brief Helper to access the nth element of a map.
 *
 * @tparam Map Map type
 * @param m Map reference
 * @param n Index of element
 * @return Reference to the nth key-value pair
 * @throws std::out_of_range if n >= m.size()
 */
template <typename Map>
auto getNth(Map &m, size_t n) -> typename Map::value_type & {
  if (n >= m.size()) {
    throw std::out_of_range("Index out of range");
  }
  auto it = m.begin();
  std::advance(it, n);
  return *it;
}

/**
 * @brief Constructs the PerformanceMaximization algorithm instance.
 */
PerformanceMaximization::PerformanceMaximization(
    ProxyManager *const kProxyManager,
    std::chrono::milliseconds const kPeriodicity, double const kDelta,
    bool const kFakeEnforce, uint64_t const kPrintLatenciesOnEntries)
    : ControlAlgorithm(kProxyManager, kPeriodicity), m_kDelta(kDelta),
      m_kFakeEnforce(kFakeEnforce),
      m_printLatenciesOnEntries(kPrintLatenciesOnEntries) {}

/**
 * @brief Main loop of the algorithm executed periodically.
 *
 * Collects cache status, computes optimal pool sizes, and enforces resizing.
 *
 * @param kProxyManager ProxyManager instance used to query and resize caches
 */
void PerformanceMaximization::loop(ProxyManager *const kProxyManager) {
  std::unordered_map<std::string, ProxyManager::CacheStatus> allCacheStatus;
  std::vector<ProxyManager::CacheResize> cacheResizes;
  bool atLeastOnePoolActive = false;

  // Timing for latency measurements
  std::chrono::duration<double, std::milli> collect(0), compute(0), enforce(0);

  // Collect status from all caches
  {
    auto start = std::chrono::high_resolution_clock::now();
    allCacheStatus = kProxyManager->getStatus();
    collect = std::chrono::high_resolution_clock::now() - start;
  }

  // Compute new pool sizes
  {
    auto start = std::chrono::high_resolution_clock::now();

    uint64_t totalSize = 0;
    int pools = 0;
    int newPools = 0;
    uint64_t usedSpace = 0;
    std::unordered_map<std::string, std::unordered_map<PoolId, uint64_t>>
        newPoolSizePerCache;

    // Step 1: update metrics history
    for (const auto &[cacheId, cacheStatus] : allCacheStatus) {
      newPoolSizePerCache[cacheId] = {};
      totalSize += cacheStatus.m_maxSize;
      for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
        if (poolStatus.m_MRC.size() < m_kMRCMinLength) {
          newPools++;
        }
        pools++;

        // Initialize metrics history if missing
        if (m_poolAvgMetricsHistory[cacheId].find(poolId) ==
            m_poolAvgMetricsHistory[cacheId].end()) {
          m_poolAvgMetricsHistory[cacheId][poolId] =
              PoolAvgMetrics{poolStatus.m_missRatio, poolStatus.m_diskIOPS,
                             poolStatus.m_throughput};
        }

        // Moving average for pool metrics
        auto &poolAvg = m_poolAvgMetricsHistory[cacheId][poolId];
        poolAvg.m_diskIOPS =
            poolAvg.m_diskIOPS * m_kMovingAverageParam +
            poolStatus.m_diskIOPS * (1 - m_kMovingAverageParam);
        poolAvg.m_missRatio =
            poolAvg.m_missRatio * m_kMovingAverageParam +
            poolStatus.m_missRatio * (1 - m_kMovingAverageParam);
        poolAvg.m_throughput =
            poolAvg.m_throughput * m_kMovingAverageParam +
            poolStatus.m_throughput * (1 - m_kMovingAverageParam);
      }
    }

    // Step 2: compute adjustment factors and preliminary new sizes
    for (const auto &[cacheId, cacheStatus] : allCacheStatus) {
      for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
        if (poolStatus.m_MRC.size() >= m_kMRCMinLength) {
          usedSpace += poolStatus.m_usedSize;
          atLeastOnePoolActive = true;
        } else {
          newPoolSizePerCache[cacheId][poolId] =
              totalSize / static_cast<double>(pools);
        }
      }
    }

    double kAdjustmentFactor =
        usedSpace
            ? (totalSize - newPools * totalSize / static_cast<double>(pools)) /
                  static_cast<double>(usedSpace)
            : 0.0;
    double kAdjustmentDelta =
        (totalSize - newPools * totalSize / static_cast<double>(pools) -
         kAdjustmentFactor * usedSpace) /
        (pools - newPools);

    // Step 3: adjust sizes for active pools
    for (const auto &[cacheId, cacheStatus] : allCacheStatus) {
      for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
        if (poolStatus.m_MRC.size() >= m_kMRCMinLength) {
          newPoolSizePerCache[cacheId][poolId] =
              std::max(0.0, poolStatus.m_usedSize * kAdjustmentFactor +
                                kAdjustmentDelta);
        }
      }
    }

    // Step 4: build optimization context
    Context context;
    double aggregatedMetrics = 0.0;

    for (const auto &[cacheId, cacheStatus] : allCacheStatus) {
      std::unordered_map<PoolId, PoolConfig> poolConfigs;
      for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
        if (poolStatus.m_MRC.size() >= m_kMRCMinLength) {
          uint64_t kSize = newPoolSizePerCache[cacheId][poolId];
          uint64_t lowerBound = static_cast<uint64_t>(
              std::max(0.0, kSize - (totalSize * m_kDelta)));

          double kAvgDiskIOPS =
              m_poolAvgMetricsHistory[cacheId][poolId].m_diskIOPS;
          double kAvgThroughput =
              m_poolAvgMetricsHistory[cacheId][poolId].m_throughput;

          std::vector<double> sizes, metrics;
          for (const auto &[s, mr] : poolStatus.m_MRC) {
            if (mr > 0.0) {
              sizes.push_back(s);
              metrics.push_back(-kAvgDiskIOPS / mr);
            }
          }

          tk::spline spline(sizes, metrics, tk::spline::cspline_hermite, true);
          double adjustment = spline(poolStatus.m_usedSize) + kAvgThroughput;
          for (auto &m : metrics)
            m += adjustment;
          spline =
              tk::spline(sizes, metrics, tk::spline::cspline_hermite, true);

          if (poolStatus.m_qosLevel > 0 &&
              poolStatus.m_qosLevel * (1 + m_kQoSMargin) > kAvgThroughput) {
            lowerBound = kSize;
          }

          aggregatedMetrics += spline(kSize);

          poolConfigs.emplace(poolId, PoolConfig{
                                          .m_optimalSize = kSize,
                                          .m_lowerBound = lowerBound,
                                          .m_upperBound = static_cast<uint64_t>(
                                              kSize + (totalSize * m_kDelta)),
                                          .m_utilityCurve = std::move(spline),
                                      });
        }
      }
      if (!poolConfigs.empty()) {
        context.m_cacheConfigs.emplace(cacheId, CacheConfig{poolConfigs});
      }
    }

    // Run optimization
    double avgMetrics = context.m_cacheConfigs.empty()
                            ? 0.0
                            : aggregatedMetrics / context.m_cacheConfigs.size();
    context.run(2000, 250, 0 /*ignored*/, avgMetrics, 90, 0.1, 1.003);

    // Update new pool sizes after optimization
    for (auto const &[cacheId, cacheConfig] : context.m_cacheConfigs) {
      for (auto const &[poolId, poolConfig] : cacheConfig.m_poolConfigs) {
        newPoolSizePerCache[cacheId][poolId] = poolConfig.m_optimalSize;
      }
    }

    // Prepare CacheResize instructions
    for (const auto &[cacheId, pools] : newPoolSizePerCache) {
      std::vector<ProxyManager::PoolResize> poolResizes;
      for (const auto &[poolId, size] : pools) {
        poolResizes.emplace_back(ProxyManager::PoolResize{
            .m_kId = poolId,
            .m_kSize =
                m_kFakeEnforce
                    ? allCacheStatus[cacheId].m_pools.at(poolId).m_maxSize
                    : size});
      }
      cacheResizes.emplace_back(ProxyManager::CacheResize{
          .m_kName = cacheId, .m_kPoolResizes = poolResizes});
    }

    compute = std::chrono::high_resolution_clock::now() - start;
  }

  // Apply new sizes to ProxyManager
  {
    auto start = std::chrono::high_resolution_clock::now();
    kProxyManager->resize(cacheResizes);
    enforce = std::chrono::high_resolution_clock::now() - start;
  }

  // Record latencies for printing if enabled
  if (m_printLatenciesOnEntries > 0 &&
      m_latencies.size() < m_printLatenciesOnEntries && atLeastOnePoolActive) {
    m_latencies.emplace_back(collect, compute, enforce);
  }

  if (m_latencies.size() == m_printLatenciesOnEntries &&
      m_printLatenciesOnEntries > 0) {
    for (auto const &[c, cm, e] : m_latencies) {
      std::cout << c.count() << "," << cm.count() << "," << e.count()
                << std::endl;
    }
    m_printLatenciesOnEntries = 0; // disable further printing
  }
}

/**
 * @brief Determines if the context should skip optimization.
 *
 * @return True if there are no pools to optimize
 */
bool PerformanceMaximization::Context::skip() const {
  return std::accumulate(m_cacheConfigs.begin(), m_cacheConfigs.end(), 0,
                         [](int acc, const auto &ccit) {
                           return acc + ccit.second.m_poolConfigs.size();
                         }) == 0;
}

/**
 * @brief Performs a single optimization step by trading pool sizes.
 */
void PerformanceMaximization::Context::step(
    double const step_size /*ignored*/) {
  // Pick two random caches
  int cacheIdx1 = randomUniformInt(m_cacheConfigs.size());
  int cacheIdx2 = randomUniformInt(m_cacheConfigs.size());
  auto &[cache1Id, cache1] = getNth(m_cacheConfigs, cacheIdx1);
  auto &[cache2Id, cache2] = getNth(m_cacheConfigs, cacheIdx2);

  // Pick pools within caches
  int poolIdx1 = randomUniformInt(cache1.m_poolConfigs.size());
  int poolIdx2 =
      (cacheIdx1 != cacheIdx2)
          ? randomUniformInt(cache2.m_poolConfigs.size())
          : (poolIdx1 + 1 + randomUniformInt(cache2.m_poolConfigs.size() - 1)) %
                cache2.m_poolConfigs.size();

  auto &[pool1Id, pool1] = getNth(cache1.m_poolConfigs, poolIdx1);
  auto &[pool2Id, pool2] = getNth(cache2.m_poolConfigs, poolIdx2);

  // Trade a random amount of space within bounds
  int maxDelta = std::min({pool1.m_optimalSize - pool1.m_lowerBound,
                           pool2.m_upperBound - pool2.m_optimalSize});

  if (maxDelta > 0) {
    int delta = randomUniformInt(maxDelta);
    pool1.m_optimalSize -= delta;
    pool2.m_optimalSize += delta;
  }
}

/**
 * @brief Computes the total energy of the context (sum of all pool metrics).
 *
 * @return Energy value
 */
double PerformanceMaximization::Context::energy() const {
  return std::accumulate(
      m_cacheConfigs.begin(), m_cacheConfigs.end(), 0.0,
      [](double acc, const auto &ccit) {
        return acc + std::accumulate(ccit.second.m_poolConfigs.begin(),
                                     ccit.second.m_poolConfigs.end(), 0.0,
                                     [](double acc, const auto &pcit) {
                                       return acc + pcit.second.getMetric();
                                     });
      });
}

/**
 * @brief Computes distance between two contexts for optimization.
 *
 * @param other Another Optimizable instance
 * @return Absolute difference in energy
 */
double
PerformanceMaximization::Context::distance(Optimizable const *other) const {
  return std::fabs(energy() - other->energy());
}

} // namespace holpaca
