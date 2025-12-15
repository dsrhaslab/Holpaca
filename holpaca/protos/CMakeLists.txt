set(_PROTOBUF_LIBPROTOBUF protobuf::libprotobuf)
set(_REFLECTION gRPC::grpc++_reflection)
set(_PROTOBUF_PROTOC $<TARGET_FILE:protobuf::protoc>)
set(_GRPC_GRPCPP gRPC::grpc++)

if(CMAKE_CROSSCOMPILING)
  find_program(_PROTOBUF_PROTOC protoc)
  find_program(_GRPC_CPP_PLUGIN_EXECUTABLE grpc_cpp_plugin)
else()
  set(_PROTOBUF_PROTOC protobuf::protoc)
  set(_GRPC_CPP_PLUGIN_EXECUTABLE $<TARGET_FILE:gRPC::grpc_cpp_plugin>)
endif()

# Proto + gRPC
get_filename_component(
  HolpacaProtoFile "${CMAKE_CURRENT_LIST_DIR}/Holpaca.proto" ABSOLUTE)
get_filename_component(HolpacaProtoPath ${HolpacaProtoFile} PATH)

# Generated sources
set(HolpacaProtoSources "${HolpacaProtoPath}/Holpaca.pb.cc")
set(HolpacaProtoHeaders "${HolpacaProtoPath}/Holpaca.pb.h")
set(HolpacaGRPCSources "${HolpacaProtoPath}/Holpaca.grpc.pb.cc")
set(HolpacaGRPCHeaders "${HolpacaProtoPath}/Holpaca.grpc.pb.h")

add_custom_command(
  OUTPUT 
    ${HolpacaProtoHeaders} 
    ${HolpacaProtoSources} 
    ${HolpacaGRPCHeaders}
    ${HolpacaGRPCSources}
  COMMAND
    ${_PROTOBUF_PROTOC} 
    ARGS 
      --grpc_out "${HolpacaProtoPath}" 
      --cpp_out  "${HolpacaProtoPath}" 
      -I "${HolpacaProtoPath}"
      --plugin=protoc-gen-grpc="${_GRPC_CPP_PLUGIN_EXECUTABLE}"
    "${HolpacaProtoFile}"
  DEPENDS 
   "${HolpacaProtoFile}"
  COMMENT 
   "Generating gRPC proto sources")

 add_library(holpaca_proto 
   ${HolpacaProtoHeaders}
   ${HolpacaProtoSources} 
   ${HolpacaGRPCHeaders} 
   ${HolpacaGRPCSources}
 )

target_link_libraries(holpaca_proto 
  PUBLIC 
  ${_REFLECTION} 
  ${_GRPC_GRPCPP}
  ${_PROTOBUF_LIBPROTOBUF}
)

install(
  TARGETS holpaca_proto 
  EXPORT holpaca-exports
  DESTINATION ${LIB_INSTALL_DIR}
)
