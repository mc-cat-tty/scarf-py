"""Original OpenCV SCARF (tests/original_impl.h, via ref_scarf) vs. the Eigen/nanobind port.

Both implementations get the same event stream and the same initialise()
arguments; the surfaces are compared at several checkpoints. Only parameter
combinations that are valid for BOTH implementations are used (the original does
no validation). Each case uses a fresh object (no re-initialisation).
"""
import os
from pathlib import Path

import numpy as np
import pytest

# (init, alpha, C) for the real 640x480 recording; init = ("size", rf_size) | ("res", (rf_w, rf_h))
REAL_CASES = [
    (("size", 40), 1.0, 0.3),
    (("size", 31), 0.5, 0.3),        # odd rf_size -> rounded up to 32
    (("size", 10), 0.25, 0.3),       # many small fields, tiny ring buffers (lots of evictions)
    (("res", (16, 12)), 1.0, 0.3),
    (("res", (8, 6)), 2.0, 0.1),
    (("res", (40, 30)), 1.5, 0.7),
]

# (img_res, init, alpha, C) for synthetic streams (non-square sizes, N == 1 ring buffer, single field ...)
SYNTH_CASES = [
    ((64, 48), ("size", 8), 1.0, 0.3),
    ((37, 101), ("size", 5), 0.7, 0.2),
    ((128, 16), ("res", (7, 1)), 1.0, 0.3),
    ((20, 20), ("res", (1, 1)), 3.0, 0.5),
    ((64, 48), ("res", (15, 11)), 0.125, 0.3),   # dims 4x4 -> N = 1
    ((33, 65), ("res", (2, 4)), 1.0, 1.0),
]
SYNTH_KINDS = ["uniform", "burst", "border", "mixed"]
SYNTH_N = 20_000
SYNTH_EVERY = 2_500
REAL_EVERY = 5_000


def _id(init, alpha, C, img_res=None):
    kind, val = init
    rf = f"rf_size={val}" if kind == "size" else f"rf_res={val[0]}x{val[1]}"
    res = f"{img_res[0]}x{img_res[1]}-" if img_res else ""
    return f"{res}{rf}-a{alpha}-C{C}"


@pytest.mark.parametrize("init,alpha,C", REAL_CASES, ids=[_id(*c) for c in REAL_CASES])
def test_real_events(real_events, run_reference, run_port, assert_surfaces_close, init, alpha, C):
    events, img_res = real_events
    ref, ref_counts = run_reference(events, img_res, init, alpha, C, REAL_EVERY)
    port, port_counts = run_port(events, img_res, init, alpha, C, REAL_EVERY)
    assert ref_counts == port_counts
    assert np.any(ref[-1] != 0), "degenerate case: reference surface is all zeros"
    assert_surfaces_close(ref, port, ref_counts, label=f"real {img_res} {_id(init, alpha, C)}")


@pytest.mark.parametrize("kind", SYNTH_KINDS)
@pytest.mark.parametrize("img_res,init,alpha,C", SYNTH_CASES, ids=[_id(c[1], c[2], c[3], c[0]) for c in SYNTH_CASES])
def test_synthetic_events(synthetic_events, run_reference, run_port, assert_surfaces_close, img_res, init, alpha, C, kind):
    seed = 1234 + 17 * SYNTH_CASES.index((img_res, init, alpha, C)) + SYNTH_KINDS.index(kind)
    events = synthetic_events(img_res[0], img_res[1], SYNTH_N, seed, kind)
    ref, ref_counts = run_reference(events, img_res, init, alpha, C, SYNTH_EVERY)
    port, port_counts = run_port(events, img_res, init, alpha, C, SYNTH_EVERY)
    assert ref_counts == port_counts
    assert_surfaces_close(ref, port, ref_counts, label=f"synthetic/{kind} {_id(init, alpha, C, img_res)}")


def test_no_events(run_reference, run_port, assert_surfaces_close):
    events = np.zeros((0, 3), dtype=np.int32)
    ref, counts = run_reference(events, (64, 48), ("size", 8), 1.0, 0.3, 0)
    port, _ = run_port(events, (64, 48), ("size", 8), 1.0, 0.3, 0)
    assert_surfaces_close(ref, port, counts, label="no events")


@pytest.mark.skipif(not os.environ.get("SCARF_FULL_DATASET"),
                    reason="set SCARF_FULL_DATASET=<path to data.h5> to run on the full recording")
def test_full_dataset(run_reference, run_port, assert_surfaces_close):
    pytest.importorskip("h5py")
    from make_fixture import load_h5_events

    ev, width, height = load_h5_events(Path(os.environ["SCARF_FULL_DATASET"]))
    events = ev[:, 1:4].astype(np.int32)  # [x, y, p]
    every = max(len(events) // 10, 1)
    for init, alpha, C in [(("size", 40), 1.0, 0.3), (("res", (16, 12)), 1.0, 0.3)]:
        ref, counts = run_reference(events, (width, height), init, alpha, C, every)
        port, _ = run_port(events, (width, height), init, alpha, C, every)
        assert_surfaces_close(ref, port, counts, label=f"full dataset {_id(init, alpha, C)}")
