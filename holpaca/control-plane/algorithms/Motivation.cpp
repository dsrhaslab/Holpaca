#include <holpaca/control-plane/ProxyManager.h>
#include <holpaca/control-plane/algorithms/Motivation.h>

namespace holpaca {

/**
 * @brief Constructs the Motivation control algorithm.
 *
 * @param kProxyManager Pointer to the ProxyManager managing caches
 * @param kPeriodicity Periodicity of loop execution
 */
Motivation::Motivation(ProxyManager *const kProxyManager,
                       std::chrono::milliseconds const kPeriodicity)
    : ControlAlgorithm(kProxyManager, kPeriodicity) {}

/**
 * @brief Main loop executed periodically to adjust cache pool sizes.
 *
 * This simple algorithm redistributes cache memory proportionally to
 * each pool’s current proportion and the cache’s overall proportion.
 *
 * @param kProxyManager ProxyManager used to query cache status and
 * resize pools
 */
void Motivation::loop(ProxyManager *const kProxyManager) {
  double sum = 0.0;      // Normalization factor for proportional allocation
  int64_t totalSize = 0; // Total cache memory across all caches
  std::vector<ProxyManager::CacheResize> cacheResizes;

  // Fetch current status of all caches and pools
  auto caches = kProxyManager->getStatus();

  // Compute normalization sum and total memory size
  for (const auto &[cacheId, cacheStatus] : caches) {
    for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
      sum += poolStatus.m_proportion * cacheStatus.m_proportion;
    }
    totalSize += cacheStatus.m_maxSize;
  }

  // Compute new pool sizes proportionally and prepare CacheResize objects
  for (const auto &[cacheId, cacheStatus] : caches) {
    std::vector<ProxyManager::PoolResize> poolResizes;
    for (const auto &[poolId, poolStatus] : cacheStatus.m_pools) {
      poolResizes.emplace_back(ProxyManager::PoolResize{
          .m_kId = poolId,
          .m_kSize = static_cast<uint64_t>(totalSize * poolStatus.m_proportion *
                                           cacheStatus.m_proportion / sum),
      });
    }
    cacheResizes.emplace_back(ProxyManager::CacheResize{
        .m_kName = cacheId, .m_kPoolResizes = poolResizes});
  }

  // Apply the computed pool sizes to the ProxyManager
  kProxyManager->resize(cacheResizes);
}

} // namespace holpaca
