cmake_minimum_required(VERSION 3.21)
project(pinpath_firmware LANGUAGES C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(PINPATH_BUILD_FIRMWARE "Build RP2040 firmware target" ON)
option(PINPATH_BUILD_TESTS "Build host tests" ON)

add_library(pinpath_core STATIC
  src/pinpath_core.cpp
)
target_include_directories(pinpath_core
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party
)
target_compile_features(pinpath_core PUBLIC cxx_std_17)

enable_testing()

if(PINPATH_BUILD_TESTS)
  add_executable(pinpath_core_tests tests/test_core.cpp)
  target_link_libraries(pinpath_core_tests PRIVATE pinpath_core)
  add_test(NAME pinpath_core_tests COMMAND pinpath_core_tests)
endif()

if(PINPATH_BUILD_FIRMWARE)
  if(NOT DEFINED PICO_SDK_PATH)
    set(PICO_SDK_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/pico-sdk")
  endif()

  if(NOT EXISTS "${PICO_SDK_PATH}/external/pico_sdk_import.cmake")
    message(FATAL_ERROR "Pico SDK not found at ${PICO_SDK_PATH}. Initialize submodule: git submodule update --init --recursive third_party/pico-sdk")
  endif()

  include(${PICO_SDK_PATH}/external/pico_sdk_import.cmake)
  pico_sdk_init()

  add_executable(pinpath_firmware src/main.cpp)
  target_link_libraries(pinpath_firmware PRIVATE pico_stdlib pinpath_core)
  target_compile_definitions(pinpath_firmware PRIVATE PICO_STDIO_USB_CONNECT_WAIT_TIMEOUT_MS=0)
  pico_enable_stdio_usb(pinpath_firmware 1)
  pico_enable_stdio_uart(pinpath_firmware 0)
  pico_add_extra_outputs(pinpath_firmware)
endif()
