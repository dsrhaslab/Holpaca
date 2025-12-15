cmake_minimum_required(VERSION 3.10)

if(NOT DEFINED PACKAGE_VERSION)
  set(PACKAGE_VERSION "1.0.0")
endif()

project("YCSB-cpp" VERSION ${PACKAGE_VERSION} LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}/cmake/" ${CMAKE_MODULE_PATH})

SET(CMAKE_INSTALL_RPATH_USE_LINK_PATH TRUE)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(INCLUDE_INSTALL_DIR include CACHE STRING "The subdirectory where header files should be installed")
set(LIB_INSTALL_DIR lib CACHE STRING "The subdirectory where libraries should be installed")
set(BIN_INSTALL_DIR bin CACHE STRING "The subdirectory where binaries should be installed")
set(CMAKE_INSTALL_DIR lib/cmake/YCSB-cpp CACHE STRING "The subdirectory where CMake package config files should be installed")

find_package(holpaca CONFIG)
find_package(RocksDB CONFIG REQUIRED)

include(GNUInstallDirs)

file(GLOB YCSB_SOURCES "core/*.cc")

add_executable(YCSB-cpp ${YCSB_SOURCES})

file(GLOB_RECURSE YCSB_SETUPS_SRC "setups/*.cc")

target_sources(YCSB-cpp PRIVATE ${YCSB_SETUPS_SRC})

target_link_libraries(YCSB-cpp PRIVATE holpaca RocksDB::rocksdb)

target_include_directories(
  YCSB-cpp
  PUBLIC 
    "$<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}>" 
    "$<INSTALL_INTERFACE:${INCLUDE_INSTALL_DIR}>" 
)

install(
  TARGETS YCSB-cpp
  EXPORT YCSB-cpp-exports 
  DESTINATION ${BIN_INSTALL_DIR}
)

install(
  DIRECTORY 
    core
    setups
    utils
  DESTINATION "${INCLUDE_INSTALL_DIR}"
  FILES_MATCHING 
    PATTERN "*.h" 
)

include(CMakePackageConfigHelpers)
configure_package_config_file(
  cmake/YCSB-cpp-config.cmake.in
  YCSB-cpp-config.cmake
  INSTALL_DESTINATION ${CMAKE_INSTALL_DIR}
  PATH_VARS
    INCLUDE_INSTALL_DIR
    CMAKE_INSTALL_DIR
)

install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/YCSB-cpp-config.cmake
  DESTINATION ${CMAKE_INSTALL_DIR}
)

install(
  EXPORT YCSB-cpp-exports
  FILE YCSB-cpp-targets.cmake
  DESTINATION ${CMAKE_INSTALL_DIR}
)
