# Standalone build of the reference driver for the ORIGINAL OpenCV-based SCARF
# (tests/original_impl.h). NOT part of the Python package build: conftest.py
# configures/builds it on demand. Manual build:
#   cmake -S tests -B tests/build/ref -DCMAKE_BUILD_TYPE=Release
#   cmake --build tests/build/ref
#
# By default OpenCV (only its `core` module, static, with bundled zlib) is
# downloaded and built from source into the build directory, so the machine
# running the tests needs no OpenCV installation. Requirements: a C/C++
# compiler, cmake >= 3.14, and network access the first time (or point
# SCARF_REF_OPENCV_URL at a local copy of the tarball, e.g.
# file:///path/opencv-4.10.0.tar.gz).
#
# Options:
#   -DSCARF_REF_SYSTEM_OPENCV=ON   use an installed OpenCV (find_package) instead
#   -DSCARF_REF_OPENCV_URL=...     source tarball to build (default: 4.10.0 from GitHub)
#   -DSCARF_REF_OPENCV_SHA256=...  expected hash of that tarball ("" disables the check)
cmake_minimum_required(VERSION 3.14)
project(scarf_reference CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if (NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

option(SCARF_REF_SYSTEM_OPENCV "Use an installed OpenCV instead of building it from source" OFF)
set(SCARF_REF_OPENCV_URL
    "https://github.com/opencv/opencv/archive/refs/tags/4.10.0.tar.gz"
    CACHE STRING "OpenCV source tarball (used when SCARF_REF_SYSTEM_OPENCV=OFF)")
set(SCARF_REF_OPENCV_SHA256
    "b2171af5be6b26f7a06b1229948bbb2bdaa74fcf5cd097e0af6378fce50a6eb9"
    CACHE STRING "SHA256 of SCARF_REF_OPENCV_URL (empty = do not verify)")

add_executable(ref_scarf ref_scarf.cpp)
target_include_directories(ref_scarf PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

if (SCARF_REF_SYSTEM_OPENCV)
  find_package(OpenCV REQUIRED COMPONENTS core)
  target_include_directories(ref_scarf PRIVATE ${OpenCV_INCLUDE_DIRS})
  target_link_libraries(ref_scarf PRIVATE ${OpenCV_LIBS})
else()
  if (WIN32)
    message(FATAL_ERROR
      "Building OpenCV from source is only wired up for Linux/macOS. "
      "On Windows configure with -DSCARF_REF_SYSTEM_OPENCV=ON.")
  endif()

  include(ExternalProject)
  if (POLICY CMP0135)
    cmake_policy(SET CMP0135 NEW)   # timestamp of extracted files = extraction time
  endif()

  set(OCV_PREFIX  ${CMAKE_CURRENT_BINARY_DIR}/opencv)          # install prefix
  set(OCV_INCLUDE ${OCV_PREFIX}/include/opencv4)
  set(OCV_LIBDIR  ${OCV_PREFIX}/lib)
  set(OCV_3PDIR   ${OCV_LIBDIR}/opencv4/3rdparty)
  set(OCV_CORE    ${OCV_LIBDIR}/libopencv_core.a)
  set(OCV_ZLIB    ${OCV_3PDIR}/libzlib.a)

  if (SCARF_REF_OPENCV_SHA256)
    set(_ocv_hash URL_HASH SHA256=${SCARF_REF_OPENCV_SHA256})
  else()
    set(_ocv_hash "")
  endif()

  # Minimal, self-contained OpenCV: core only, static, no optional third-party
  # libraries (OPENCV_FORCE_3RDPARTY_BUILD builds zlib from the bundled sources
  # instead of picking up whatever the host has).
  ExternalProject_Add(opencv_ep
    URL               ${SCARF_REF_OPENCV_URL}
    ${_ocv_hash}
    PREFIX            ${CMAKE_CURRENT_BINARY_DIR}/opencv-ep
    CMAKE_ARGS
      -DCMAKE_BUILD_TYPE=Release
      -DCMAKE_INSTALL_PREFIX=${OCV_PREFIX}
      -DCMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5
      -DBUILD_LIST=core
      -DBUILD_SHARED_LIBS=OFF
      -DBUILD_opencv_world=OFF
      -DBUILD_TESTS=OFF
      -DBUILD_PERF_TESTS=OFF
      -DBUILD_EXAMPLES=OFF
      -DBUILD_DOCS=OFF
      -DBUILD_JAVA=OFF
      -DBUILD_opencv_apps=OFF
      -DBUILD_ZLIB=ON
      -DOPENCV_FORCE_3RDPARTY_BUILD=ON
      -DOPENCV_GENERATE_PKGCONFIG=OFF
      -DENABLE_PRECOMPILED_HEADERS=OFF
      -DWITH_IPP=OFF
      -DWITH_ITT=OFF
      -DWITH_OPENCL=OFF
      -DWITH_OPENMP=OFF
      -DWITH_TBB=OFF
      -DWITH_EIGEN=OFF
      -DWITH_LAPACK=OFF
      -DWITH_CUDA=OFF
      -DWITH_PROTOBUF=OFF
      -DWITH_CAROTENE=OFF
      # fixed install layout (some distros would otherwise use lib64)
      -DOPENCV_LIB_INSTALL_PATH=lib
      -DOPENCV_3P_LIB_INSTALL_PATH=lib/opencv4/3rdparty
      -DOPENCV_INCLUDE_INSTALL_PATH=include/opencv4
    BUILD_COMMAND     ${CMAKE_COMMAND} --build <BINARY_DIR> --parallel
    BUILD_BYPRODUCTS  ${OCV_CORE} ${OCV_ZLIB}
  )

  # Imported targets for the static libs produced above. The include directory
  # must exist at configure time, before the external project has run.
  file(MAKE_DIRECTORY ${OCV_INCLUDE})
  find_package(Threads REQUIRED)

  add_library(ocv_zlib STATIC IMPORTED)
  set_target_properties(ocv_zlib PROPERTIES IMPORTED_LOCATION ${OCV_ZLIB})

  add_library(ocv_core STATIC IMPORTED)
  set_target_properties(ocv_core PROPERTIES
    IMPORTED_LOCATION             ${OCV_CORE}
    INTERFACE_INCLUDE_DIRECTORIES ${OCV_INCLUDE})
  set(_ocv_sys Threads::Threads ${CMAKE_DL_LIBS})
  if (UNIX AND NOT APPLE)
    list(APPEND _ocv_sys rt)
  endif()
  set_property(TARGET ocv_core PROPERTY INTERFACE_LINK_LIBRARIES ocv_zlib ${_ocv_sys})

  add_dependencies(ocv_core opencv_ep)
  target_link_libraries(ref_scarf PRIVATE ocv_core)
endif()
