add_library(holpaca_orchestrator_lib
  Orchestrator.h
  Orchestrator.cpp
  ProxyManager.h
  algorithms/Optimizable.h
  algorithms/ControlAlgorithm.h
  algorithms/PerformanceMaximization.h
  algorithms/PerformanceMaximization.cpp
  algorithms/Motivation.h
  algorithms/Motivation.cpp
)

target_link_libraries(holpaca_orchestrator_lib PUBLIC
  holpaca_proto
  GSL::gsl
)

install(
  TARGETS holpaca_orchestrator_lib
  EXPORT holpaca-exports
  DESTINATION ${LIB_INSTALL_DIR})

add_executable(holpaca_orchestrator
  Main.cpp
)

target_link_libraries(holpaca_orchestrator PUBLIC
  holpaca_orchestrator_lib
)

install(
  TARGETS holpaca_orchestrator 
  EXPORT holpaca-exports
  DESTINATION ${BIN_INSTALL_DIR})

