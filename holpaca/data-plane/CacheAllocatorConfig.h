#pragma once

#include <cachelib/allocator/CacheAllocatorConfig.h>

namespace holpaca {

// CacheAllocatorConfig extends CacheLib's CacheAllocatorConfig with
// holpaca-specific configuration used by the data plane.
template <typename CacheT>
class CacheAllocatorConfig
    : public ::facebook::cachelib::CacheAllocatorConfig<
          ::facebook::cachelib::CacheAllocator<typename CacheT::Trait>> {

  // Address on which the agent exposes its gRPC server
  std::string m_address;

  // Address of the orchestrator gRPC endpoint
  std::string m_orchestratorAddress;

  // Cache size exposed to the orchestrator
  int64_t m_virtualSize;

  // Indicates whether a virtual size was explicitly configured
  bool m_hasVirtualSize{false};

  // MOTIVATION ONLY: proportion of the instance relative to other instances
  double proportion{1.0};

public:
  // Sets the gRPC address for this agent
  CacheAllocatorConfig &setAddress(std::string address) {
    m_address = address;
    return *this;
  }

  // Sets the orchestrator gRPC address
  CacheAllocatorConfig &setOrchestratorAddress(std::string address) {
    m_orchestratorAddress = address;
    return *this;
  }

  // Sets the virtual size exposed to the orchestrator
  CacheAllocatorConfig &setVirtualSize(uint64_t size) {
    m_hasVirtualSize = true;
    m_virtualSize = size;
    return *this;
  }

  // MOTIVATION ONLY: sets the proportion of this instance
  CacheAllocatorConfig &setProportion(double proportion) {
    this->proportion = proportion;
    return *this;
  }

  friend CacheT;
};

} // namespace holpaca
