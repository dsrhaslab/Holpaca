cmake_minimum_required(VERSION 3.10)

if(NOT DEFINED PACKAGE_VERSION)
  set(PACKAGE_VERSION "1.0.0")
endif()

project("holpaca" VERSION ${PACKAGE_VERSION} LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}/cmake/" ${CMAKE_MODULE_PATH})

SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(INCLUDE_INSTALL_DIR include/holpaca CACHE STRING "The subdirectory where header files should be installed")
set(LIB_INSTALL_DIR lib CACHE STRING "The subdirectory where libraries should be installed")
set(BIN_INSTALL_DIR bin CACHE STRING "The subdirectory where binaries should be installed")
set(CMAKE_INSTALL_DIR lib/cmake/holpaca CACHE STRING "The subdirectory where CMake package config files should be installed")

find_package(cachelib CONFIG REQUIRED)
find_package(shards CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
find_package(gRPC CONFIG REQUIRED)
find_package(GSL REQUIRED)

include(GNUInstallDirs)

add_library(holpaca INTERFACE)

# Add root dir so qualified includes work
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/..)

add_subdirectory(protos)
add_subdirectory(data-plane)
add_subdirectory(control-plane)

target_link_libraries(holpaca INTERFACE
  holpaca_orchestrator_lib
  holpaca_agent
  holpaca_proto
)
target_include_directories(
  holpaca
  INTERFACE 
  "$<INSTALL_INTERFACE:${INCLUDE_INSTALL_DIR}>" 
)

install(
  DIRECTORY  
    "data-plane"
    "control-plane"
    "protos"
  DESTINATION "${INCLUDE_INSTALL_DIR}"
  FILES_MATCHING 
    PATTERN "*.h" 
)

include(CMakePackageConfigHelpers)
configure_package_config_file(
  cmake/holpaca-config.cmake.in
  holpaca-config.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_DIR}
  PATH_VARS
    INCLUDE_INSTALL_DIR
    CMAKE_INSTALL_DIR
)

install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/holpaca-config.cmake
  DESTINATION ${CMAKE_INSTALL_DIR}
)

install(TARGETS holpaca
  EXPORT holpaca-exports
  DESTINATION ${LIB_INSTALL_DIR}
)

install(
  EXPORT holpaca-exports
  FILE holpaca-targets.cmake
  DESTINATION ${CMAKE_INSTALL_DIR}
)
