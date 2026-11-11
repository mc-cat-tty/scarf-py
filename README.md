# SCARF Python

[![Tests](https://github.com/mc-cat-tty/scarf-py/actions/workflows/tests.yml/badge.svg)](https://github.com/mc-cat-tty/scarf-py/actions/workflows/tests.yml)

Python (nanobind-ed) porting of the SCARF (Set of Center Active Receptive Fields) velocity invariant events representation.

By installing this package you will get a Python class with the following functionalities:
```python
class SCARF(builtins.object)
 |  SCARF(*args, **kwargs)
 |
 |  Methods defined here:
 |
 |  __init__(...)
 |      __init__(self) -> None
 |
 |  getAll(...)
 |      getAll(self, u: int, v: int) -> list[tuple[int, int]]
 |
 |      Get a list of all events, in <x, y> format, stored in the receptive at coordinates <u, v>
 |
 |  getList(...)
 |      getList(self, u: int, v: int) -> list[tuple[int, int]]
 |
 |      Get a list of active events, in <x, y> format, stored in the receptive at coordinates <u, v>
 |
 |  getN(...)
 |      getN(self) -> int
 |
 |      Get receptive field's circular buffer capacity (max num of elements)
 |
 |  getScarfParams(...)
 |      getScarfParams(self) -> tuple[tuple[int, int], tuple[int, int], int, tuple[int, int]]
 |
 |      Get SCARF parameters as <count, dims, N, border_shift>:
 |              count        : Resolution of SCARF blocks
 |              dims         : Size of receptive field
 |              N            : Size of ring buffer in each SCARF block
 |              border_shift : (HARD CORDED) pixel values for shift size to match origin of image and origin of scarf
 |
 |  getSurface(...)
 |      getSurface(self) -> numpy.ndarray[dtype=float64, shape=(*, *), order='C']
 |
 |      Get a reference the SCARF surface as a 2D matrix
 |
 |  initialise(...)
 |      initialise(self, img_res: tuple[int, int], rf_size: int, alpha: float = 1.0, C: float = 0.3) -> None
 |      initialise(self, img_res: tuple[int, int], rf_res: tuple[int, int], alpha: float = 1.0, C: float = 0.3) -> None
 |
 |      Overloaded function.
 |
 |      1. ``initialise(self, img_res: tuple[int, int], rf_size: int, alpha: float = 1.0, C: float = 0.3) -> None``
 |
 |      Initialize from receptive field size
 |
 |      2. ``initialise(self, img_res: tuple[int, int], rf_res: tuple[int, int], alpha: float = 1.0, C: float = 0.3) -> None``
 |
 |      Initialize from receptive field resolution
 |
 |  update(...)
 |      update(self, u: int, v: int, p: int) -> None
 |
 |      Update the surface with an incoming event: <u, v, polarity>
```

## Installation
### Quick way (suggested)
Download the wheel (*.whl*) file compatible with your platform (arch and OS) from the latest release, then run:
```bash
pip install <scarf_py-VERSION-cp312-abi3-PLATOFRM>.whl
```

## Build from source
Download this repository, then run:
```bash
pip install .
```

Make sure that you have `cmake` and a C++ compiler installed in your working environment, otherwise installation will fail
while trying to compile the bindings and the C++ source code. Also, ensure that access to the network is available and that
`curl` and `git` are installed into your systems: they are needed to build Eigen3 from source.

After the installation a Python module named `scarf` will be availabe:
```python
import scarf

s = scarf.SCARF()
s.initialise((100, 100), (10, 10))
s.update(5, 5, 1)
s.update(5, 5, 0)
s.update(15, 15, 1)
surf = s.getSurface()
...
```

## Results

Speed of the Python binding (this project) compared with a pure-Python CPU implementation (numpy + torch) and the native C++ code.

### Common setup
| | |
|---|---|
| CPU | Intel Xeon Silver 4310 @ 2.10 GHz (24 cores / 48 threads) |
| Architecture | x86_64 |
| RAM | 503 GB |
| OS / toolchain | Ubuntu 24.04, Linux 7.0, Python 3.12.3, NumPy 2.5.4, g++ 13.3.0 (`-O3 -DNDEBUG`) |
| Data | Real sequence from H3.6M dataset; 500,000 events from a 640×480 sensor |
| SCARF parameters | Receptive field size = 40, alpha = 1.0, C = 0.3 |
| Runs | 10 per implementation; each recreating the SCARF object from scratch and processing the whole slice |
| Metric | Only event processing is timed. Speedup refers to the improvement compared to the pure-Python baseline; values are mean ± sample std dev over the 10 runs. |

### Table
| Implementation | Hardware used | ns/event | Mevents/s | Speedup vs pure Python |
|---|---|---|---|---|
| Pure Python (NumPy + PyTorch) | CPU only (single thread) | 6743.3 ± 127.4 | 0.148 ± 0.003 | 1.00 ± 0.02 |
| Python binding (nanobind, `SCARF.update()` called per event from a Python loop) | CPU only (single thread) | 200.4 ± 7.7 | 4.996 ± 0.174 | 33.7 ± 1.2 |
| Native C++ (`scarf.h` called directly, no Python) | CPU only (single thread) | 67.3 ± 1.3 | 14.874 ± 0.285 | 100.3 ± 1.9 |

On this stream the binding and `scarf.py` produce the same surface (max absolute difference 7e-7, from float32 vs float64 accumulation).
The binding is ~3× slower than native C++ because of the per-call Python/nanobind overhead.

## Running the AI-generated tests

The test suite checks two things: that the Python port gives the **same results as the original C++ implementation**, and that **bad inputs raise clean Python exceptions** instead of crashing the interpreter.

### Quick start
```bash
pip install . pytest numpy
pytest tests
```
The tests run in about 10 seconds. The very first run is slower because it also builds the reference program (see below).

### What is tested
- **Equivalence with the original** (`tests/test_equivalence.py`): the same stream of events is fed to the original OpenCV-based implementation (`tests/original_impl.h`, run from a small C++ program) and to the Python port, and the resulting surfaces are compared at several checkpoints. Inputs are a 50k-event slice of a real recording (Human3.6M, 640x480) plus seeded synthetic streams, with several parameter sets covering both `initialise` overloads.
- **Edge inputs** (`tests/test_edge_inputs.py`): out-of-range coordinates, invalid sizes, wrong types, `update` before `initialise`, and so on. Each must raise the expected exception (`ValueError`, `IndexError`, `RuntimeError`, `TypeError`). Cases that could crash run in a subprocess, so a crash shows up as a failed test.

Two tests are marked as *expected failures* (`XFAIL` in the output). They document known limitations, not regressions: a NumPy array obtained from `getSurface()` dangles if you re-initialise with a different size, and coordinates of 4096 or more wrap around (inherited from the original).

### The reference program
The original implementation is compiled automatically on the first run, into `tests/build/ref`, and reused afterwards. You do **not** need OpenCV installed: the build downloads OpenCV 4.10.0 and compiles only its `core` module, statically.

You need:
- a C/C++ compiler and `cmake` 3.14 or newer;
- network access the first time (the build takes one to a few minutes, depending on your cores);
- Linux or macOS. On Windows, use an installed OpenCV (see below).

If the reference can't be built, the equivalence tests are **skipped** with the reason shown. Set `SCARF_REQUIRE_REF=1` to turn that into a failure, which is what you want in CI.

### Options
| Setting | What it does |
|---|---|
| `SCARF_REQUIRE_REF=1` | Fail instead of skip when the reference can't be built. |
| `SCARF_REF_BINARY=<path>` | Use an already built `ref_scarf` and skip the build. |
| `SCARF_REF_CMAKE_ARGS="-DSCARF_REF_OPENCV_URL=file:///path/opencv-4.10.0.tar.gz"` | Build OpenCV from a local tarball (offline machines). |
| `SCARF_REF_CMAKE_ARGS="-DSCARF_REF_SYSTEM_OPENCV=ON -DOpenCV_DIR=<dir>"` | Use an installed OpenCV instead of building one. |
| `--scarf-rtol` / `--scarf-atol` (or `SCARF_RTOL` / `SCARF_ATOL`) | Comparison tolerance, see below. |
| `SCARF_FULL_DATASET=<data.h5>` | Also run the comparison on a full recording: `SCARF_FULL_DATASET=<data.h5> pytest tests -k full_dataset`. Needs `h5py`. Skipped by default. |

### Tolerance
Surfaces are compared with NumPy's `isclose` rule: `|port - reference| <= atol + rtol * |reference|`. The defaults are `rtol=1e-9` and `atol=1e-12`. In practice the two implementations currently agree exactly, so you can run with `--scarf-rtol 0 --scarf-atol 0`. A mismatch reports the checkpoint, the number of differing pixels, the largest difference and the first differing pixel.

### Test data
The small real-data fixture lives in `tests/data/h36m_cam2_S11_Directions_slice.npz`. To regenerate it from a full recording (needs `h5py`):
```bash
python tests/make_fixture.py --h5 <path/to/data.h5>
```

## Credits
The original C++ implementation, found in `cpp-impl`, comes from [IIT's `robotology/event-driven` repository](https://github.com/robotology/event-driven/tree/main/ev2/event-driven/algs).

Motivations and working principles of SCARF can be found in the following papers (not mine):
```
@misc{ikura2026eventpreservingvelocityinvariant,
    title={An Event Preserving Velocity Invariant Representation for Event Cameras}, 
    author={Mikihiro Ikura and Luna Gava and Jiahang Wu and Chiara Bartolozzi and Arren Glover},
    year={2026},
    eprint={2609.19973},
    archivePrefix={arXiv},
    primaryClass={cs.CV},
    url={https://arxiv.org/abs/2609.19973}, 
}

@inproceedings{gava2025scarf,
    title={{SCARF}: A Set of Centre Active Receptive Fields for Velocity Invariant Event Representation},
    author={Luna Gava and Mikihiro Ikura and Chiara Bartolozzi and Arren Glover},
    booktitle={IROS 2025 Workshop on Neuromorphic Perception for Real World Robotics (NeuRobots)},
    year={2025},
    url={https://openreview.net/forum?id=Oc7PzozG2s}
}
```