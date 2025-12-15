#include <grpcpp/create_channel.h>
#include <holpaca/data-plane/CacheAllocator.h>
#include <shards/ShardsConfig.h>

namespace holpaca {

/**
 * @brief Constructs a CacheAllocator instance.
 *
 * Initializes the base CacheLib allocator, sets up gRPC communication with
 * the orchestrator, and starts the local gRPC server if addresses are provided.
 */
template <typename CacheTrait>
CacheAllocator<CacheTrait>::CacheAllocator(Config &config)
    : ::facebook::cachelib::CacheAllocator<CacheTrait>(config),
      // Address on which this agent exposes its gRPC server
      m_kAddress(config.m_address),
      // Cache size exposed to the orchestrator (default is physical size)
      m_kVirtualSize(config.m_hasVirtualSize ? config.m_virtualSize
                                             : config.size),
      // MOTIVATION ONLY: proportion of instance relative to other instances
      m_kProportion(config.proportion) {

  // Reserve space to avoid reallocations during runtime.
  // CacheLib only supports up to 64 pools per cache instance.
  m_shards.reserve(64);
  m_metrics.reserve(64);
  m_qosLevels.reserve(64);
  m_proportions.reserve(64);

  // Start gRPC server and connect to orchestrator if both addresses are set
  if (!m_kAddress.empty() && !config.m_orchestratorAddress.empty()) {

    // Build and start the AgentRPC gRPC server
    m_server =
        grpc::ServerBuilder()
            .AddListeningPort(m_kAddress, grpc::InsecureServerCredentials())
            .RegisterService(dynamic_cast<AgentRPC::Service *>(this))
            .BuildAndStart();

    // Run the gRPC server in a dedicated thread
    m_serverThread = std::thread([this] { m_server->Wait(); });

    // Create a stub for communicating with the orchestrator
    m_orchestrator =
        std::make_shared<OrchestratorRPC::Stub>(grpc::CreateChannel(
            config.m_orchestratorAddress, grpc::InsecureChannelCredentials()));

    // Register this cache agent with the orchestrator
    ::grpc::ClientContext context;
    ConnectRequest request;
    ConnectResponse response;
    request.set_cacheaddress(m_kAddress);

    ::grpc::Status status;

    // Retry until the orchestrator becomes available
    do {
      status = m_orchestrator->Connect(&context, request, &response);
      std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    } while (!status.ok());
  }
}

/**
 * @brief Handles Resize RPC requests from the orchestrator.
 *
 * CacheLib resizes pools using relative deltas rather than absolute sizes.
 * This function computes relative changes, sorts them, and applies resizing
 * from most-shrunk to most-grown to ensure total size constraints.
 */
template <typename CacheTrait>
grpc::Status CacheAllocator<CacheTrait>::Resize(grpc::ServerContext *context,
                                                const ResizeRequest *request,
                                                ResizeResponse *response) {

  std::vector<std::pair<PoolId, int64_t>> sortedRelSizes{}; // may be negative

  // Compute per-pool relative size changes
  for (const auto &[poolId, targetSize] : request->poolsizes()) {
    auto const originalSize = Super::getPool(poolId).getPoolSize();
    if (targetSize != originalSize) {
      sortedRelSizes.push_back({static_cast<PoolId>(poolId),
                                static_cast<int64_t>(targetSize) -
                                    static_cast<int64_t>(originalSize)});
    }
  }

  // Resizing must be done from the most-shrunk pool to the most-grown pool
  // This ensures all changes are possible while staying under total cache size
  std::sort(sortedRelSizes.begin(), sortedRelSizes.end(),
            [](const auto &a, const auto &b) { return a.second < b.second; });

  // Apply resize operations
  for (auto [poolId, relSize] : sortedRelSizes) {
    if (relSize < 0) {
      Super::shrinkPool(poolId, -relSize);
    } else {
      Super::growPool(poolId, relSize);
    }
  }

  return grpc::Status::OK;
}

/**
 * @brief Destructor shuts down gRPC services and notifies orchestrator.
 */
template <typename CacheTrait> CacheAllocator<CacheTrait>::~CacheAllocator() {

  // Notify orchestrator that this cache agent is disconnecting
  if (m_orchestrator) {
    ::grpc::ClientContext context;
    DisconnectRequest request;
    DisconnectResponse response;
    request.set_cacheaddress(m_kAddress);
    m_orchestrator->Disconnect(&context, request, &response);
  }

  // Gracefully shut down the gRPC server
  if (m_server) {
    m_server->Shutdown();
    m_serverThread.join();
  }
}

/**
 * @brief Handles GetStatus RPC requests from the orchestrator.
 *
 * Returns cache- and pool-level statistics including MRC, runtime metrics,
 * QoS level, and pool proportion.
 */
template <typename CacheTrait>
grpc::Status
CacheAllocator<CacheTrait>::GetStatus(grpc::ServerContext *context,
                                      const GetStatusRequest *request,
                                      GetStatusResponse *response) {

  auto cacheStatus = response->mutable_cachestatus();
  auto pools = cacheStatus->mutable_pools();

  cacheStatus->set_maxsize(
      std::min(m_kVirtualSize, Super::getCacheMemoryStats().ramCacheSize));

  // MOTIVATION ONLY: proportion of this cache instance
  cacheStatus->set_proportion(m_kProportion);

  // Populate status for each active pool
  for (const auto &poolId : Super::getPoolIds()) {
    const auto &pool = Super::getPool(poolId);
    bool const isActive = m_activePools.find(poolId) != m_activePools.end();

    if (isActive) {
      PoolStatus poolStatus;

      // Fill miss ratio curve (MRC) and runtime metrics
      auto const &mrc = m_shards[poolId]->byteMRC();
      auto [diskIOPS, missRatio, throughput] = m_metrics[poolId];
      *poolStatus.mutable_mrc() = {mrc.begin(), mrc.end()};
      poolStatus.set_diskiops(diskIOPS);
      poolStatus.set_missratio(missRatio);
      poolStatus.set_throughput(throughput);

      // QoS level assigned to this pool
      poolStatus.set_qos(m_qosLevels[poolId]);

      // MOTIVATION ONLY: proportion assigned to this pool
      poolStatus.set_proportion(m_proportions[poolId]);

      // CacheLib pool statistics
      poolStatus.set_poolid(poolId);
      poolStatus.set_maxsize(pool.getPoolSize());
      poolStatus.set_usedsize(pool.getCurrentAllocSize());

      (*pools)[poolId] = poolStatus;
    }
  }

  return grpc::Status::OK;
}

/**
 * @brief Adds a new cache pool with optional size, QoS, and proportion.
 *
 * Also initializes a SHARDS MRC generator for the pool.
 */
template <typename CacheTrait>
PoolId CacheAllocator<CacheTrait>::addPool(std::string name, size_t size,
                                           double qosLevel, double proportion) {

  // Create a new CacheLib pool (blocks until enough memory is available if size
  // != 0)
  PoolId poolId = Super::addPool(name, size);

  // Create MRC generation engine for the new pool
  shards::ShardsConfig config;
  config.setAcceptanceRate(0.001).setBucketSize(100).setMaxSize(
      this->getCacheMemoryStats().ramCacheSize);

  m_shards[poolId] = std::make_shared<shards::Shards>(std::move(config));
  m_qosLevels[poolId] = qosLevel;
  m_metrics[poolId] = {0, 1.0, 0}; // diskIOPS, missRatio, throughput
  m_proportions[poolId] = proportion;
  m_activePools.insert(poolId);

  return poolId;
}

/**
 * @brief Intercepts the find operation and updates MRC statistics.
 */
template <typename CacheTrait>
typename CacheAllocator<CacheTrait>::ReadHandle
CacheAllocator<CacheTrait>::find(typename CacheAllocator<CacheTrait>::Key key) {

  auto handle = Super::find(key);

  // Update MRC statistics on cache hit
  if (handle) {
    auto const kPoolId =
        Super::getAllocInfo(static_cast<const void *>(handle->getMemory()))
            .poolId;

    std::string keyStr(key.data(), key.size());
    uint32_t size = handle->getSize();
    m_shards[kPoolId]->accessed(keyStr, size);
  }

  return handle;
}

/**
 * @brief Intercepts insert operation and updates shard statistics.
 */
template <typename CacheTrait>
bool CacheAllocator<CacheTrait>::insert(
    const typename CacheAllocator<CacheTrait>::WriteHandle &handle) {

  bool const success = Super::insert(handle);

  // Update shard statistics on successful insert
  if (success) {
    PoolId pid =
        Super::getAllocInfo(static_cast<const void *>(handle->getMemory()))
            .poolId;

    auto key = handle->getKey();
    std::string keyStr(key.data(), key.size());
    uint32_t size = handle->getSize();

    // Remove old entry from MRC and record the new object
    m_shards[pid]->remove(keyStr);
    m_shards[pid]->accessed(keyStr, size);
  }

  return success;
}

/**
 * @brief Intercepts insertOrReplace operation and updates shard statistics.
 */
template <typename CacheTrait>
typename CacheAllocator<CacheTrait>::WriteHandle
CacheAllocator<CacheTrait>::insertOrReplace(
    const typename CacheAllocator<CacheTrait>::WriteHandle &handle) {

  auto oldHandle = Super::insertOrReplace(handle);

  // Update shard statistics if an existing entry was replaced
  if (oldHandle) {
    PoolId pid =
        Super::getAllocInfo(static_cast<const void *>(handle->getMemory()))
            .poolId;

    auto key = handle->getKey();
    std::string keyStr(key.data(), key.size());
    uint32_t size = handle->getSize();

    m_shards[pid]->remove(keyStr);
    m_shards[pid]->accessed(keyStr, size);
  }

  return oldHandle;
}

/**
 * @brief Registers runtime metrics for a given pool.
 */
template <typename CacheTrait>
void CacheAllocator<CacheTrait>::registerMetrics(PoolId poolId,
                                                 uint32_t diskIOPS,
                                                 double missRatio,
                                                 uint32_t throughput) {
  m_metrics[poolId] = {diskIOPS, missRatio, throughput};
}

/**
 * @brief Removes a cache pool and releases all its memory.
 */
template <typename CacheTrait>
void CacheAllocator<CacheTrait>::removePool(PoolId id) {
  // Mark pool as inactive
  m_activePools.erase(id);

  // Shrink pool to release memory
  Super::shrinkPool(id, Super::getPool(id).getPoolSize());
}

// Explicit template instantiations for supported eviction policies
template class CacheAllocator<::facebook::cachelib::LruCacheTrait>;
template class CacheAllocator<
    ::facebook::cachelib::LruCacheWithSpinBucketsTrait>;
template class CacheAllocator<::facebook::cachelib::Lru2QCacheTrait>;
template class CacheAllocator<::facebook::cachelib::TinyLFUCacheTrait>;

} // namespace holpaca
