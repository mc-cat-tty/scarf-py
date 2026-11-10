"""Shared fixtures for the SCARF test-suite.

Reference build (original OpenCV implementation, tests/original_impl.h):
  built on demand from tests/CMakeLists.txt into ``tests/build/ref`` (gitignored).
  Environment knobs:
    SCARF_REF_BINARY     path to an already built ``ref_scarf`` (skips the build)
    SCARF_REF_BUILD_DIR  build directory (default: tests/build/ref)
    SCARF_REF_CMAKE_ARGS extra cmake configure args. By default OpenCV (core only) is downloaded and
                         built from source by tests/CMakeLists.txt, so no OpenCV install is needed.
                         Useful args: "-DSCARF_REF_OPENCV_URL=file:///path/opencv-4.10.0.tar.gz" (offline)
                         or "-DSCARF_REF_SYSTEM_OPENCV=ON -DOpenCV_DIR=/opt/opencv/lib/cmake/opencv4"
                         (use an installed OpenCV instead; the OpenCV_DIR env var also works then)
    SCARF_REQUIRE_REF=1  fail instead of skip when the reference can't be built

Comparison tolerance (numpy.isclose semantics, |port - ref| <= atol + rtol * |ref|):
  --scarf-rtol / --scarf-atol on the command line, else SCARF_RTOL / SCARF_ATOL,
  else the defaults below.
"""
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

TESTS_DIR = Path(__file__).resolve().parent
FIXTURE_NPZ = TESTS_DIR / "data" / "h36m_cam2_S11_Directions_slice.npz"

DEFAULT_RTOL = 1e-9
DEFAULT_ATOL = 1e-12


# --------------------------------------------------------------------------- options
def pytest_addoption(parser):
    group = parser.getgroup("scarf")
    group.addoption("--scarf-rtol", type=float, default=None,
                    help=f"relative tolerance for original-vs-port surfaces (env SCARF_RTOL, default {DEFAULT_RTOL})")
    group.addoption("--scarf-atol", type=float, default=None,
                    help=f"absolute tolerance for original-vs-port surfaces (env SCARF_ATOL, default {DEFAULT_ATOL})")


def _tol(config, opt, env, default):
    val = config.getoption(opt)
    if val is None:
        val = float(os.environ[env]) if os.environ.get(env) else default
    return val


@pytest.fixture(scope="session")
def tolerance(pytestconfig):
    return {
        "rtol": _tol(pytestconfig, "--scarf-rtol", "SCARF_RTOL", DEFAULT_RTOL),
        "atol": _tol(pytestconfig, "--scarf-atol", "SCARF_ATOL", DEFAULT_ATOL),
    }


def pytest_report_header(config):
    return (f"scarf tolerance: rtol={_tol(config, '--scarf-rtol', 'SCARF_RTOL', DEFAULT_RTOL)}, "
            f"atol={_tol(config, '--scarf-atol', 'SCARF_ATOL', DEFAULT_ATOL)}")


@pytest.fixture(scope="session")
def assert_surfaces_close(tolerance):
    """Return ``check(ref, port, counts, label)`` comparing stacks of surfaces (k, h, w)."""
    rtol, atol = tolerance["rtol"], tolerance["atol"]

    def check(ref, port, counts=None, label=""):
        assert ref.shape == port.shape, f"{label}: shape mismatch ref={ref.shape} port={port.shape}"
        for k in range(ref.shape[0]):
            r, q = ref[k], port[k]
            ok = np.isclose(q, r, rtol=rtol, atol=atol, equal_nan=True)
            if ok.all():
                continue
            diff = np.abs(q - r)
            with np.errstate(divide="ignore", invalid="ignore"):
                rel = np.where(r != 0, diff / np.abs(r), np.where(diff == 0, 0.0, np.inf))
            row, col = map(int, np.argwhere(~ok)[0])
            n_ev = counts[k] if counts is not None else "?"
            pytest.fail(
                f"{label}: surfaces differ at checkpoint {k} (after {n_ev} events) with rtol={rtol}, atol={atol}: "
                f"{int((~ok).sum())} pixels out of tolerance; max abs diff={np.nanmax(diff):.6g}, "
                f"max rel diff={np.nanmax(rel):.6g}; first differing (row, col)=({row}, {col}): "
                f"ref={r[row, col]!r} port={q[row, col]!r}"
            )

    return check


# --------------------------------------------------------------------------- reference build
def _find_cmake():
    exe = shutil.which("cmake")
    if exe:
        return exe
    cand = Path(sys.executable).parent / "cmake"  # e.g. `pip install cmake` in the venv
    return str(cand) if cand.exists() else None


def _build_reference():
    """Return (path or None, error message)."""
    if os.environ.get("SCARF_REF_BINARY"):
        p = Path(os.environ["SCARF_REF_BINARY"])
        return (p, "") if p.is_file() else (None, f"SCARF_REF_BINARY={p} does not exist")
    cmake = _find_cmake()
    if cmake is None:
        return None, "cmake not found (install it or `pip install cmake`)"
    build_dir = Path(os.environ.get("SCARF_REF_BUILD_DIR", TESTS_DIR / "build" / "ref"))
    build_dir.mkdir(parents=True, exist_ok=True)
    extra = shlex.split(os.environ.get("SCARF_REF_CMAKE_ARGS", ""))
    steps = [
        [cmake, "-S", str(TESTS_DIR), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release", *extra],
        [cmake, "--build", str(build_dir), "--config", "Release"],
    ]
    for cmd in steps:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            tail = "\n".join((res.stdout + res.stderr).strip().splitlines()[-15:])
            return None, (
                f"`{' '.join(cmd)}` failed (OpenCV is built from source: needs a C/C++ compiler, cmake >= 3.14 "
                f"and network access for the first build; see tests/CMakeLists.txt for offline/system-OpenCV "
                f"options):\n{tail}"
            )
    for cand in (build_dir / "ref_scarf", build_dir / "Release" / "ref_scarf.exe", build_dir / "ref_scarf.exe"):
        if cand.is_file():
            return cand, ""
    return None, f"ref_scarf binary not found in {build_dir}"


@pytest.fixture(scope="session")
def ref_binary():
    path, err = _build_reference()
    if path is None:
        msg = f"original (OpenCV) reference implementation unavailable: {err}"
        if os.environ.get("SCARF_REQUIRE_REF"):
            pytest.fail(msg)
        pytest.skip(msg)
    return path


# --------------------------------------------------------------------------- runners
def _init_kwargs(init):
    kind, val = init
    if kind == "size":
        return {"rf_size": int(val)}
    if kind == "res":
        return {"rf_res": tuple(int(x) for x in val)}
    raise ValueError(kind)


@pytest.fixture(scope="session")
def run_reference(ref_binary, tmp_path_factory):
    """``run(events(n,3), img_res, init, alpha, C, every_k) -> (surfaces (k,h,w), counts)``."""

    def run(events, img_res, init, alpha, C, every_k):
        d = tmp_path_factory.mktemp("ref")
        ev_path, out_path = d / "events.bin", d / "surfaces.bin"
        np.ascontiguousarray(events, dtype="<i4").tofile(ev_path)
        kind, val = init
        rf_args = [str(val)] if kind == "size" else [str(val[0]), str(val[1])]
        cmd = [str(ref_binary), str(ev_path), str(out_path), str(img_res[0]), str(img_res[1]),
               str(every_k), kind, *rf_args, repr(float(alpha)), repr(float(C))]
        res = subprocess.run(cmd, capture_output=True, text=True)
        assert res.returncode == 0, f"reference failed ({res.returncode}): {res.stderr}"
        counts = [int(x) for x in res.stdout.split()]
        width, height = img_res
        surf = np.fromfile(out_path, dtype=np.float64).reshape(-1, height, width)
        assert surf.shape[0] == len(counts)
        return surf, counts

    return run


@pytest.fixture(scope="session")
def run_port():
    """Same contract as ``run_reference`` but drives the nanobind ``scarf`` module."""
    scarf = pytest.importorskip("scarf")

    def run(events, img_res, init, alpha, C, every_k):
        s = scarf.SCARF()
        s.initialise(img_res=tuple(img_res), alpha=alpha, C=C, **_init_kwargs(init))
        snaps, counts = [], []
        n = 0
        for n, (u, v, p) in enumerate(np.asarray(events).tolist(), start=1):
            s.update(u, v, p)
            if every_k > 0 and n % every_k == 0:
                snaps.append(np.array(s.getSurface(), dtype=np.float64, copy=True))
                counts.append(n)
        if not counts or counts[-1] != n:
            snaps.append(np.array(s.getSurface(), dtype=np.float64, copy=True))
            counts.append(n)
        return np.stack(snaps), counts

    return run


# --------------------------------------------------------------------------- event data
@pytest.fixture(scope="session")
def real_events():
    """Real h36m slice: (events int32 (n, 3) as [u=x, v=y, p], (width, height))."""
    if not FIXTURE_NPZ.exists():
        pytest.skip(f"{FIXTURE_NPZ} missing; regenerate with tests/make_fixture.py")
    with np.load(FIXTURE_NPZ) as z:
        ev = np.stack([z["x"], z["y"], z["p"]], axis=1).astype(np.int32)
        width, height = (int(x) for x in z["sensor_size"])
    return ev, (width, height)


def make_synthetic_events(width, height, n, seed, kind="mixed"):
    """Seeded synthetic stream (n, 3) int32 [u, v, p], all in bounds.

    kind: "uniform" (random pixels), "burst" (one pixel repeated), "border"
    (pixels on the image border, corners always included first), "mixed"
    (uniform, burst, border, uniform segments back to back).
    """
    rng = np.random.default_rng(seed)
    if kind == "uniform":
        u, v = rng.integers(0, width, n), rng.integers(0, height, n)
    elif kind == "burst":
        u, v = np.full(n, rng.integers(0, width)), np.full(n, rng.integers(0, height))
    elif kind == "border":
        xs, ys = np.arange(width), np.arange(height)
        border = np.concatenate([
            np.stack([xs, np.zeros_like(xs)], 1), np.stack([xs, np.full_like(xs, height - 1)], 1),
            np.stack([np.zeros_like(ys), ys], 1), np.stack([np.full_like(ys, width - 1), ys], 1),
        ])
        corners = np.array([[0, 0], [width - 1, 0], [0, height - 1], [width - 1, height - 1]])
        pts = np.concatenate([corners, border[rng.integers(0, len(border), max(n - 4, 0))]])[:n]
        u, v = pts[:, 0], pts[:, 1]
    elif kind == "mixed":
        sizes = [n // 4, n // 4, n // 4, n - 3 * (n // 4)]
        kinds = ["uniform", "burst", "border", "uniform"]
        parts = [make_synthetic_events(width, height, m, seed + i + 1, k) for i, (m, k) in enumerate(zip(sizes, kinds))]
        return np.concatenate(parts).astype(np.int32)
    else:
        raise ValueError(kind)
    p = rng.integers(0, 2, n)
    return np.stack([u, v, p], axis=1).astype(np.int32)


@pytest.fixture(scope="session")
def synthetic_events():
    return make_synthetic_events
