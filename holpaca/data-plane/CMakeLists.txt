add_library(holpaca_agent
  CacheAllocator.h
  CacheAllocatorConfig.h
  CacheAllocator.cpp
)

target_link_libraries(holpaca_agent PUBLIC
  cachelib_allocator
  holpaca_proto
  shards
)

install(
  TARGETS holpaca_agent 
  EXPORT holpaca-exports
  DESTINATION ${LIB_INSTALL_DIR}
)
