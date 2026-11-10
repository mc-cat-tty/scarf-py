
cmake_minimum_required(VERSION 3.5)

project( scarfinator )
find_package(Eigen3 REQUIRED NO_MODULE)

if (CMAKE_VERSION VERSION_LESS 3.18)
  set(DEV_MODULE Development)
else()
  set(DEV_MODULE Development.Module)
endif()

find_package(Python 3.10 COMPONENTS Interpreter ${DEV_MODULE} REQUIRED)

if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Choose the type of build." FORCE)
  set_property(CACHE CMAKE_BUILD_TYPE PROPERTY STRINGS "Debug" "Release" "MinSizeRel" "RelWithDebInfo")
endif()

execute_process(
  COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
  OUTPUT_STRIP_TRAILING_WHITESPACE OUTPUT_VARIABLE nanobind_DIR)
find_package(nanobind CONFIG REQUIRED)

include_directories(cpp-impl/)
nanobind_add_module(scarf cpp-impl/scarf.cpp STABLE_ABI)

nanobind_add_stub(
  scarf_stub
  MODULE scarf
  OUTPUT scarf.pyi
  PYTHON_PATH $<TARGET_FILE_DIR:scarf>
  DEPENDS scarf
)

target_link_libraries(scarf PRIVATE Eigen3::Eigen)

install(TARGETS scarf LIBRARY DESTINATION .)
install(FILES ${CMAKE_BINARY_DIR}/scarf.pyi DESTINATION .)
