import cppyy
from pathlib import Path
import cv2 as cv

# pkg-config --cflags opencv4

LOG_PATH = Path("/home/fmecatti-iit.local/moveenet-v2/datasets/h36m/cam2_S11_Directions/ch0dvs/data.log")
OPENCV_PATH = Path("/usr/include/opencv4")

cppyy.add_include_path(OPENCV_PATH.as_posix())
cppyy.include("scarf.h")

from cppyy.gbl import scarf

res = (1280, 720)

s = scarf.SCARF()
s.initialise(res, 14, 1.0, 0.3)