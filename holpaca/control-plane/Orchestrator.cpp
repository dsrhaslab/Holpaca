#include <grpcpp/create_channel.h>
#include <grpcpp/server_builder.h>
#include <grpcpp/server_context.h>
#include <holpaca/control-plane/Orchestrator.h>

#include <numeric>

namespace holpaca {

/**
 * @brief Collects status information from all connected agents.
 *
 * For each registered proxy, issues a GetStatus RPC and aggregates
 * cache- and pool-level statistics into a unified structure consumed
 * by control algorithms.
 *
 * @return Map of cache names (address) to their CacheStatus
 */
std::unordered_map<std::string, ProxyManager::CacheStatus>
Orchestrator::getStatus() {
  std::unordered_map<std::string, ProxyManager::CacheStatus> cacheStatus;

  for (const auto &[peer, proxy] : m_proxies) {
    ::grpc::ClientContext context;
    GetStatusRequest request;
    GetStatusResponse response;

    // Synchronous RPC to fetch status from the agent
    proxy->GetStatus(&context, request, &response);

    // Populate top-level cache status
    cacheStatus[peer] = ProxyManager::CacheStatus{
        .m_maxSize = response.cachestatus().maxsize(),
        .m_proportion = response.cachestatus().proportion(),
        .m_pools = {},
    };

    // Populate per-pool statistics
    for (const auto &[poolId, ps] : response.cachestatus().pools()) {
      cacheStatus[peer].m_pools[poolId] = ProxyManager::PoolStatus{
          .m_maxSize = ps.maxsize(),
          .m_usedSize = ps.usedsize(),
          .m_diskIOPS = ps.diskiops(),
          .m_throughput = ps.throughput(),
          .m_missRatio = ps.missratio(),
          .m_qosLevel = ps.qos(),
          .m_proportion = ps.proportion(),
          .m_MRC = {ps.mrc().begin(), ps.mrc().end()},
      };
    }
  }

  return cacheStatus;
}

/**
 * @brief Issues resize commands to all connected agents.
 *
 * Each CacheResize operation corresponds to one active proxy.
 * If the number of operations does not match the number of proxies,
 * resizing is skipped.
 *
 * @param cacheResize Vector of CacheResize instructions
 */
void Orchestrator::resize(
    const std::vector<ProxyManager::CacheResize> &cacheResize) {

  // Ensure one resize operation per connected agent
  if (cacheResize.size() != m_proxies.size()) {
    return;
  }

  for (const auto &resizeOp : cacheResize) {
    auto proxy = m_proxies[resizeOp.m_kName];
    ::grpc::ClientContext context;
    ResizeRequest request;
    ResizeResponse response;

    // Populate target pool sizes
    auto sizes = request.mutable_poolsizes();
    for (const auto &poolResize : resizeOp.m_kPoolResizes) {
      (*sizes)[poolResize.m_kId] = poolResize.m_kSize;
    }

    // Synchronous resize RPC
    proxy->Resize(&context, request, &response);
  }
}

/**
 * @brief Registers a new agent and creates a gRPC stub for it.
 *
 * @param context gRPC server context
 * @param request ConnectRequest containing the cache address
 * @param response ConnectResponse to fill
 * @return grpc::Status OK if successful
 */
grpc::Status Orchestrator::Connect(grpc::ServerContext *context,
                                   const ConnectRequest *request,
                                   ConnectResponse *response) {
  m_proxies[request->cacheaddress()] = AgentRPC::NewStub(grpc::CreateChannel(
      request->cacheaddress(), grpc::InsecureChannelCredentials()));
  return grpc::Status::OK;
}

/**
 * @brief Removes an agent from the orchestrator.
 *
 * @param context gRPC server context
 * @param request DisconnectRequest containing the cache address
 * @param response DisconnectResponse to fill
 * @return grpc::Status OK if successful
 */
grpc::Status Orchestrator::Disconnect(grpc::ServerContext *context,
                                      const DisconnectRequest *request,
                                      DisconnectResponse *response) {
  m_proxies.erase(request->cacheaddress());
  return grpc::Status::OK;
}

/**
 * @brief Starts the orchestrator gRPC server and launches its event loop.
 *
 * @param kOrchestratorAddress Address to bind the gRPC server to
 */
Orchestrator::Orchestrator(const std::string &kOrchestratorAddress)
    : m_kServer(grpc::ServerBuilder()
                    .AddListeningPort(kOrchestratorAddress,
                                      grpc::InsecureServerCredentials())
                    .RegisterService(static_cast<Orchestrator::Service *>(this))
                    .BuildAndStart()),
      m_serverThread([this] { m_kServer->Wait(); }) {}

/**
 * @brief Gracefully shuts down the orchestrator and stops all background
 * activity.
 */
Orchestrator::~Orchestrator() {
  m_controlAlgorithm.reset();
  m_stop.exchange(true);

  if (m_kServer != nullptr) {
    m_kServer->Shutdown();
  }

  if (m_serverThread.joinable()) {
    m_serverThread.join();
  }
}

} // namespace holpaca
