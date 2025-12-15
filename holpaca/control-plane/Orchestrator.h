#pragma once

#include <grpcpp/server.h>
#include <holpaca/control-plane/ProxyManager.h>
#include <holpaca/control-plane/algorithms/ControlAlgorithm.h>
#include <holpaca/protos/Holpaca.grpc.pb.h>
#include <holpaca/protos/Holpaca.pb.h>

#include <atomic>
#include <thread>
#include <unordered_map>

namespace holpaca {

/**
 * @brief Orchestrator implements the control-plane gRPC service.
 * Coordinates multiple agents, manages cache status, and applies resizing
 * decisions.
 */
class Orchestrator : public OrchestratorRPC::Service, public ProxyManager {

  /* gRPC server instance for the orchestrator */
  std::shared_ptr<grpc::Server> const m_kServer;

  /* Thread running the gRPC server event loop */
  std::thread m_serverThread;

  /* Indicates whether the orchestrator is shutting down */
  std::atomic_bool m_stop{false};

  /* Map of cache address to AgentRPC stubs for communicating with agents */
  std::unordered_map<std::string, std::shared_ptr<AgentRPC::Stub>> m_proxies;

  /* Active control algorithm used to compute cache resizing decisions */
  std::unique_ptr<ControlAlgorithm> m_controlAlgorithm;

  /**
   * @brief Registers an agent with the orchestrator
   * @param context gRPC server context
   * @param request ConnectRequest from the agent
   * @param response ConnectResponse to fill
   * @return gRPC status of the operation
   */
  grpc::Status Connect(grpc::ServerContext *context,
                       const ConnectRequest *request,
                       ConnectResponse *response);

  /**
   * @brief Unregisters an agent from the orchestrator
   * @param context gRPC server context
   * @param request DisconnectRequest from the agent
   * @param response DisconnectResponse to fill
   * @return gRPC status of the operation
   */
  grpc::Status Disconnect(grpc::ServerContext *context,
                          const DisconnectRequest *request,
                          DisconnectResponse *response);

  /**
   * @brief Retrieves the current status of all connected caches
   * @return Map of cache names to their CacheStatus
   */
  std::unordered_map<std::string, ProxyManager::CacheStatus>
  getStatus() override final;

  /**
   * @brief Applies resize decisions to connected caches
   * @param cacheResize Vector of CacheResize instructions
   */
  void resize(
      const std::vector<ProxyManager::CacheResize> &cacheResize) override final;

public:
  /**
   * @brief Constructs and starts the orchestrator gRPC server on the given
   * address
   * @param kOrchestratorAddress Address for the gRPC server
   */
  Orchestrator(const std::string &kOrchestratorAddress);

  /**
   * @brief Gracefully shuts down the orchestrator and all active connections
   */
  ~Orchestrator();

  /**
   * @brief Installs a control algorithm
   * @tparam T ControlAlgorithm type
   * @tparam Args Arguments for algorithm constructor
   * @param args Constructor arguments for the algorithm
   * @return Reference to this Orchestrator for chaining
   */
  template <typename T, typename... Args>
  Orchestrator &addAlgorithm(Args... args) {
    m_controlAlgorithm =
        std::make_unique<T>(dynamic_cast<ProxyManager *const>(this), args...);
    return *this;
  }
};

} // namespace holpaca
