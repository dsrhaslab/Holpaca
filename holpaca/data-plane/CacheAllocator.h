#pragma once

// CacheLib allocator base
#include <cachelib/allocator/CacheAllocator.h>

// gRPC core and C++ bindings
#include <grpc/grpc.h>
#include <grpcpp/server.h>
#include <grpcpp/server_builder.h>
#include <grpcpp/server_context.h>

// Holpaca-specific configuration and protobuf definitions
#include <holpaca/data-plane/CacheAllocatorConfig.h>
#include <holpaca/protos/Holpaca.grpc.pb.h>
#include <holpaca/protos/Holpaca.pb.h>

// MRC generation
#include <shards/Shards.h>

#include <mutex>
#include <unordered_map>
#include <unordered_set>

namespace holpaca {

// Pool identifiers used by CacheLib
using PoolId = ::facebook::cachelib::PoolId;

/**
 * @brief CacheAllocator extends Facebook CacheLib's allocator with
 * gRPC-based control-plane features (AgentRPC).
 *
 * @tparam CacheTrait Determines the eviction policy (LRU, TinyLFU, etc.)
 */
template <typename CacheTrait>
class CacheAllocator : public ::facebook::cachelib::CacheAllocator<CacheTrait>,
                       public holpaca::AgentRPC::Service {

  // ======================
  // gRPC-related members
  // ======================

  /* Local AgentRPC service implementation */
  std::shared_ptr<AgentRPC::Service> m_agent;

  /* Stub to communicate with the orchestrator */
  std::shared_ptr<OrchestratorRPC::Stub> m_orchestrator;

  /* Background thread running the gRPC server */
  std::thread m_serverThread;

  /* gRPC server instance */
  std::shared_ptr<grpc::Server> m_server{nullptr};

  /* Address this agent listens on */
  std::string const m_kAddress;

  /**
   * @brief Handles GetStatus RPC requests from the orchestrator.
   */
  grpc::Status GetStatus(grpc::ServerContext *context,
                         const GetStatusRequest *request,
                         GetStatusResponse *response) override final;

  /**
   * @brief Handles Resize RPC requests from the orchestrator.
   *
   * Dynamically resizes cache pools.
   */
  grpc::Status Resize(grpc::ServerContext *context,
                      const ResizeRequest *request,
                      ResizeResponse *response) override final;

  // ======================
  // End gRPC-related code
  // ======================

  /* Alias for the base CacheLib allocator */
  using Super = ::facebook::cachelib::CacheAllocator<CacheTrait>;

  /* MRC generation engine per pool */
  std::unordered_map<PoolId, std::shared_ptr<shards::Shards>> m_shards;

  /* Runtime performance metrics per pool:
   *   - disk IOPS
   *   - miss ratio
   *   - throughput
   */
  std::unordered_map<PoolId, std::tuple<uint32_t, double, uint32_t>> m_metrics;

  /* Set of currently active pools */
  std::unordered_set<PoolId> m_activePools;

  /* Minimum throughput demand per pool */
  std::unordered_map<PoolId, double> m_qosLevels;

  /* Motivation algorithm: proportion each pool should get within the cache */
  std::unordered_map<PoolId, double> m_proportions;

  /* Observed size by the orchestrator */
  uint64_t const m_kVirtualSize{0};

  /* Motivation-only: proportion of this instance relative to others */
  double const m_kProportion{1.0};

public:
  /* Type of allocator configuration */
  using Config = CacheAllocatorConfig<CacheAllocator<CacheTrait>>;

  /* Eviction policy trait */
  using Trait = CacheTrait;

  /* CacheLib handle aliases */
  using ReadHandle = typename Super::ReadHandle;
  using WriteHandle = typename Super::WriteHandle;
  using Key = typename Super::Key;

  /**
   * @brief Constructs a CacheAllocator with the given configuration.
   *
   * Starts the gRPC server and initializes agent communication.
   *
   * @param config CacheAllocator configuration object
   */
  CacheAllocator(Config &config);

  /**
   * @brief Destructor shuts down gRPC services and releases resources.
   */
  ~CacheAllocator();

  /**
   * @brief Adds a new cache pool.
   *
   * @param name Name of the pool
   * @param size Optional size of the pool
   * @param qosLevel Optional minimum throughput requirement
   * @param proportion Optional proportional allocation (for Motivation)
   * @return PoolId Identifier of the created pool
   */
  PoolId addPool(std::string name, size_t size = 0, double qosLevel = 0.0,
                 double proportion = 1.0);

  /**
   * @brief Intercepts the find operation of the underlying CacheLib allocator.
   *
   * @param key Key to look up
   * @return ReadHandle Handle to the cached object
   *    or nullptr if not found
   */
  ReadHandle find(Key key);

  /**
   * @brief Intercepts the insert operation of the underlying CacheLib
   * allocator.
   *
   * @param handle Write handle for the object
   * @return true if insertion succeeded
   */
  bool insert(const WriteHandle &handle);

  /**
   * @brief Intercepts insertOrReplace operation of the underlying CacheLib.
   *
   * @param handle Write handle for the object
   * @return WriteHandle Updated handle
   */
  WriteHandle insertOrReplace(const WriteHandle &handle);

  /**
   * @brief Registers performance metrics for a pool.
   *
   * @param poolId Pool identifier
   * @param diskIOPS Disk I/O operations per second
   * @param missRatio Cache miss ratio
   * @param throughput Throughput of the pool
   */
  void registerMetrics(PoolId poolId, uint32_t diskIOPS, double missRatio,
                       uint32_t throughput);

  /**
   * @brief Removes a cache pool and cleans up associated state.
   *
   * @param id Pool identifier to remove
   */
  void removePool(PoolId id);
};

/* Common CacheAllocator typedefs for different eviction policies */
using LruAllocator = CacheAllocator<facebook::cachelib::LruCacheTrait>;
using LruWithSpinAllocator =
    CacheAllocator<facebook::cachelib::LruCacheWithSpinBucketsTrait>;
using Lru2QAllocator = CacheAllocator<facebook::cachelib::Lru2QCacheTrait>;
using TinyLFUAllocator = CacheAllocator<facebook::cachelib::TinyLFUCacheTrait>;

} // namespace holpaca
