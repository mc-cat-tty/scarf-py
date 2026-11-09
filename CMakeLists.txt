
cmake_minimum_required(VERSION 3.5)
project( scarfinator )
find_package( OpenCV REQUIRED )
include_directories( ${OpenCV_INCLUDE_DIRS} )
message( ${OpenCV_INCLUDE_DIRS} )