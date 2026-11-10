# SCARF Python
Python (nanobind-ed) porting of the SCARF (Set of Center Active Receptive Fields) velocity invariant events representation.

By installing this package you will get a Python class with the following functionalities:
```
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

## Credits
The original C++ implementation, found in `cpp-impl` comes from [IIT's `robotology/event-driven` repository](https://github.com/robotology/event-driven/tree/main/ev2/event-driven/algs).

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