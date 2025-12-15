#pragma once

#include <cachelib/allocator/memory/Slab.h>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

namespace holpaca {

using PoolId = ::facebook::cachelib::PoolId;

/**
 * @brief Abstract interface for managing caches and their memory pools.
 * Provides methods to get status and resize caches.
 */
class ProxyManager {
public:
  /**
   * @brief Status information for a single memory pool.
   */
  struct PoolStatus {
    uint64_t m_maxSize{0};             /* Maximum pool size in bytes */
    uint64_t m_usedSize{0};            /* Current memory used */
    uint32_t m_diskIOPS{0};            /* Disk I/O operations per second */
    uint32_t m_throughput{0};          /* Throughput in Ops/sec */
    double m_missRatio{1.0};           /* Cache miss ratio */
    double m_qosLevel{0.0};            /* Minimum throughput demand */
    double m_proportion{1.0};          /* MOTIVATION ONLY: pool proportion */
    std::map<uint64_t, float> m_MRC{}; /* Miss Ratio Curve */
  };

  /**
   * @brief Status information for a whole cache.
   */
  struct CacheStatus {
    uint64_t m_maxSize{0};    /* Cache capacity in bytes */
    double m_proportion{1.0}; /* MOTIVATION ONLY: cache proportion */
    std::unordered_map<PoolId, PoolStatus> m_pools{}; /* Status of each pool */
  };

  /**
   * @brief Represents a resize operation for a single pool.
   */
  struct PoolResize {
    PoolId m_kId;     /* Pool ID */
    uint64_t m_kSize; /* New size */
  };

  /**
   * @brief Represents a resize operation for a cache.
   */
  struct CacheResize {
    std::string m_kName;                    /* Cache name (agent address) */
    std::vector<PoolResize> m_kPoolResizes; /* Pool resize operations */
  };

  /**
   * @brief Get the status of all caches.
   * @return Map of cache names to their status
   */
  virtual std::unordered_map<std::string, CacheStatus> getStatus() = 0;

  /**
   * @brief Resize one or more caches and their pools.
   * @param cacheResize Vector of resize instructions
   */
  virtual void resize(const std::vector<CacheResize> &cacheResize) = 0;
};

} // namespace holpaca
