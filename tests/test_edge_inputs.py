"""Edge-input tests for the Python bindings of ``scarf.SCARF``.

Only binding-level / validation behaviour is asserted here; the SCARF algorithm
itself is covered by the comparison against the original in test_equivalence.py.
Cases that could plausibly crash the interpreter (out-of-range writes, state
corruption) run in a subprocess, so a segfault is reported as a test failure.
"""
import subprocess
import sys
import textwrap

import numpy as np
import pytest

scarf = pytest.importorskip("scarf")

W, H = 64, 48  # non-square on purpose


def run_isolated(body, timeout=60):
    """Run ``body`` in a fresh ``python -I`` with ``scarf`` and ``np`` imported."""
    code = "import scarf, numpy as np\n" + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=timeout)


def assert_no_crash(res):
    assert res.returncode == 0, (
        f"subprocess exited with {res.returncode}"
        f"{' (killed by signal %d)' % -res.returncode if res.returncode < 0 else ''}\n"
        f"stdout: {res.stdout}\nstderr: {res.stderr[-2000:]}"
    )


def raised_in_subprocess(setup, call):
    """Return the exception class name raised by ``call`` (or None), crash-safe."""
    body = f"{textwrap.dedent(setup)}\ntry:\n    {call}\nexcept BaseException as e:\n    print('RAISED', type(e).__name__)\nelse:\n    print('NO-RAISE')\n"
    res = run_isolated(body)
    assert_no_crash(res)
    out = res.stdout.split()
    return out[out.index("RAISED") + 1] if "RAISED" in out else None


def fresh(img_res=(W, H), rf_size=8):
    s = scarf.SCARF()
    s.initialise(img_res, rf_size)
    return s


INIT_SETUP = f"s = scarf.SCARF(); s.initialise(({W}, {H}), 8)"


# --------------------------------------------------------------------------- update()
def test_update_before_initialise_raises_runtime_error():
    assert raised_in_subprocess("s = scarf.SCARF()", "s.update(0, 0, 1)") == "RuntimeError"


@pytest.mark.parametrize("u,v", [
    (-1, 0), (0, -1), (-1, -1),
    (W, 0), (0, H), (W, H), (W - 1, H), (W, H - 1),
    (10**6, 0), (0, 10**6),
    (2**31 - 1, 0), (0, 2**31 - 1), (-(2**31), 0), (0, -(2**31)),
])
def test_update_out_of_range_raises_index_error(u, v):
    assert raised_in_subprocess(INIT_SETUP, f"s.update({u}, {v}, 1)") == "IndexError"


@pytest.mark.parametrize("u,v,p", [
    (2**31, 0, 1), (-(2**31) - 1, 0, 1), (0, 2**40, 1), (2**64, 0, 1), (0, 0, 2**31), (0, 0, -(2**31) - 1),
])
def test_update_beyond_int32_raises_type_error(u, v, p):
    # nanobind's int caster rejects values that don't fit a C int -> overload resolution fails
    assert raised_in_subprocess(INIT_SETUP, f"s.update({u}, {v}, {p})") == "TypeError"


@pytest.mark.parametrize("bad", [1.0, "1", None, [1], np.float64(1.0)])
@pytest.mark.parametrize("pos", [0, 1, 2])
def test_update_wrong_types_raise_type_error(bad, pos):
    s = fresh()
    args = [1, 1, 1]
    args[pos] = bad
    with pytest.raises(TypeError):
        s.update(*args)


def test_update_edges_and_corners_in_bounds_do_not_raise():
    s = fresh()
    for u, v in [(0, 0), (W - 1, 0), (0, H - 1), (W - 1, H - 1)]:
        s.update(u, v, 1)


@pytest.mark.parametrize("p", [0, 1, 3, 4, 7, 8, -1, -4, -5, 100, 2**31 - 1, -(2**31)])
def test_update_extreme_polarity_does_not_crash(p):
    # p is stored in a 3-bit signed bit-field (wraps); only check nothing blows up
    res = run_isolated(f"""
        {INIT_SETUP}
        for u, v in [(0, 0), ({W // 2}, {H // 2}), ({W - 1}, {H - 1})] * 50:
            s.update(u, v, {p})
        s.getSurface().sum()
        print("OK")
    """)
    assert_no_crash(res)
    assert "OK" in res.stdout


# --------------------------------------------------------------------------- initialise() validation
@pytest.mark.parametrize("img_res", [(0, H), (W, 0), (0, 0), (-W, H), (W, -H), (-1, -1)])
@pytest.mark.parametrize("rf", [8, (4, 4)], ids=["rf_size", "rf_res"])
def test_initialise_non_positive_image_raises_value_error(img_res, rf):
    with pytest.raises(ValueError):
        scarf.SCARF().initialise(img_res, rf)


@pytest.mark.parametrize("rf_size", [0, -1, -8])
def test_initialise_non_positive_rf_size_raises_value_error(rf_size):
    with pytest.raises(ValueError):
        scarf.SCARF().initialise((W, H), rf_size)


@pytest.mark.parametrize("rf_size", [W, 100, 10**6])
def test_initialise_rf_size_larger_than_image_raises_value_error(rf_size):
    with pytest.raises(ValueError):
        scarf.SCARF().initialise((W, H), rf_size)


@pytest.mark.parametrize("rf_res", [(0, 4), (4, 0), (-1, 4), (4, -1)])
def test_initialise_non_positive_rf_res_raises_value_error(rf_res):
    with pytest.raises(ValueError):
        scarf.SCARF().initialise((W, H), rf_res)


@pytest.mark.parametrize("rf_res", [(W, H), (1000, 4), (4, 1000), (W // 2, H // 2)])
def test_initialise_grid_too_fine_raises_value_error(rf_res):
    # positive grid, but the receptive-field dims collapse to 0 (or < 2 and rounded down to 0)
    with pytest.raises(ValueError):
        scarf.SCARF().initialise((W, H), rf_res)


@pytest.mark.parametrize("alpha", [0.0, -1.0, 1e-3])
@pytest.mark.parametrize("rf", [8, (4, 4)], ids=["rf_size", "rf_res"])
def test_initialise_non_positive_or_tiny_alpha_raises_value_error(alpha, rf):
    with pytest.raises(ValueError):
        scarf.SCARF().initialise((W, H), rf, alpha)


@pytest.mark.parametrize("img_res", [(), (W,), (W, H, 1), [], [W], [W, H, 1]])
def test_initialise_wrong_tuple_length_raises_type_error(img_res):
    with pytest.raises(TypeError):
        scarf.SCARF().initialise(img_res, 8)


@pytest.mark.parametrize("rf_res", [(), (4,), (4, 4, 4)])
def test_initialise_wrong_rf_res_length_raises_type_error(rf_res):
    with pytest.raises(TypeError):
        scarf.SCARF().initialise((W, H), rf_res)


@pytest.mark.parametrize("img_res", [W, None, "ab", {W, H}, {"w": W, "h": H}, np.array([W, H]), range(2)],
                         ids=["int", "None", "str", "set", "dict", "ndarray", "range"])
def test_initialise_non_tuple_image_raises_type_error(img_res):
    with pytest.raises(TypeError):
        scarf.SCARF().initialise(img_res, 8)


@pytest.mark.parametrize("img_res", [(float(W), H), (W, float(H)), (str(W), H), (None, H), (2**31, H)])
def test_initialise_wrong_element_types_raise_type_error(img_res):
    with pytest.raises(TypeError):
        scarf.SCARF().initialise(img_res, 8)


@pytest.mark.parametrize("kwargs", [
    {"rf_size": 8.0}, {"rf_size": "8"}, {"rf_size": None}, {"rf_res": (4.0, 4)},
    {"rf_size": 8, "alpha": "x"}, {"rf_size": 8, "C": None},
])
def test_initialise_wrong_argument_types_raise_type_error(kwargs):
    with pytest.raises(TypeError):
        scarf.SCARF().initialise((W, H), **kwargs)


def test_initialise_accepts_lists():
    s = scarf.SCARF()
    s.initialise([W, H], 8)
    assert s.getSurface().shape == (H, W)
    s.initialise([W, H], [4, 4])
    assert s.getSurface().shape == (H, W)


# --------------------------------------------------------------------------- state / shapes
def test_get_surface_before_initialise_is_empty():
    a = scarf.SCARF().getSurface()
    assert a.dtype == np.float64
    assert a.shape == (0, 0)


@pytest.mark.parametrize("img_res", [(64, 48), (37, 101), (128, 16), (20, 20)])
def test_surface_dtype_and_shape(img_res):
    for rf in (4, (1, 1)):
        s = scarf.SCARF()
        s.initialise(img_res, rf)
        a = s.getSurface()
        assert a.dtype == np.float64
        assert a.shape == (img_res[1], img_res[0])  # (height, width)


def test_keyword_arguments_both_overloads():
    s = scarf.SCARF()
    s.initialise(img_res=(30, 20), rf_size=4, alpha=0.5, C=0.1)
    assert s.getSurface().shape == (20, 30)
    s.initialise(img_res=(30, 20), rf_res=(3, 2), alpha=0.5, C=0.1)
    assert s.getSurface().shape == (20, 30)
    s.initialise((30, 20), 4)          # defaults for alpha / C
    s.initialise((30, 20), (3, 2))
    s.update(u=1, v=2, p=1)


def test_reinitialise_with_new_size_changes_shape():
    s = fresh()
    s.update(10, 10, 1)
    s.initialise((100, 30), (5, 2))
    a = s.getSurface()
    assert a.shape == (30, 100)
    assert not a.any()
    s.update(99, 29, 1)  # in bounds for the new size
    with pytest.raises(IndexError):
        s.update(0, 30, 1)


FAILED_INIT_CALLS = [
    "s.initialise((0, 48), 8)",
    "s.initialise((64, 48), 0)",
    "s.initialise((64, 48), 100)",
    "s.initialise((64, 48), (64, 48))",
    "s.initialise((64, 48), (0, 4))",
    "s.initialise((128, 96), 8, 0.0)",
    "s.initialise((128, 96), (4, 4), -1.0)",
    "s.initialise((64,), 8)",
    "s.initialise((64.0, 48), 8)",
]


@pytest.mark.parametrize("bad_call", FAILED_INIT_CALLS)
def test_failed_initialise_leaves_object_unchanged(bad_call):
    # Compare against a twin that never saw the failed call: same events -> same surface.
    res = run_isolated(f"""
        rng = np.random.default_rng(7)
        ev = np.stack([rng.integers(0, 37, 3000), rng.integers(0, 101, 3000), rng.integers(0, 2, 3000)], 1).tolist()
        s, twin = scarf.SCARF(), scarf.SCARF()
        for o in (s, twin):
            o.initialise((37, 101), 6, 0.7, 0.2)
        for u, v, p in ev[:1500]:
            s.update(u, v, p); twin.update(u, v, p)
        before = s.getSurface().copy()
        try:
            {bad_call}
        except (ValueError, TypeError):
            pass
        else:
            raise SystemExit("bad call did not raise")
        after = s.getSurface()
        assert after.shape == (101, 37), after.shape
        assert np.array_equal(after, before)
        for u, v, p in ev[1500:]:
            s.update(u, v, p); twin.update(u, v, p)
        assert np.array_equal(s.getSurface(), twin.getSurface())
        try:
            s.update(37, 0, 1)
        except IndexError:
            print("OK")
    """)
    assert_no_crash(res)
    assert "OK" in res.stdout


def test_failed_initialise_on_fresh_object_keeps_it_uninitialised():
    res = run_isolated("""
        s = scarf.SCARF()
        for call in (lambda: s.initialise((0, 10), 2), lambda: s.initialise((64, 48), (64, 48))):
            try:
                call()
            except ValueError:
                pass
        assert s.getSurface().shape == (0, 0)
        try:
            s.update(0, 0, 1)
        except RuntimeError:
            print("OK")
    """)
    assert_no_crash(res)
    assert "OK" in res.stdout


# --------------------------------------------------------------------------- known problems (findings)
@pytest.mark.xfail(strict=True, reason=(
    "getSurface() returns a view (rv_policy::reference_internal) into the C++ matrix; a later "
    "initialise() with a different size reallocates it, leaving earlier arrays dangling "
    "(use-after-free, segfault for large surfaces)"))
def test_surface_array_survives_reinitialise():
    res = run_isolated("""
        s = scarf.SCARF()
        s.initialise((640, 480), 40)
        s.update(100, 100, 1)
        a = s.getSurface()
        expected = float(a.sum())
        s.initialise((320, 240), 40)
        assert float(a.sum()) == expected
        print("OK")
    """)
    assert_no_crash(res)
    assert "OK" in res.stdout


@pytest.mark.xfail(strict=True, reason=(
    "CARF stores u/v in 13-bit signed bit-fields (inherited from the original): for u or v >= 4096 "
    "the coordinate wraps and the event is written to a different pixel (or out of bounds)"))
def test_update_wide_surface_writes_own_pixel():
    # On a fresh surface the only pixel an event can change is its own (v, u).
    res = run_isolated("""
        s = scarf.SCARF()
        s.initialise((9000, 10), (1, 1))
        s.update(5000, 3, 1)
        nz = np.argwhere(s.getSurface()).tolist()
        print("NZ", nz)
        assert nz == [[3, 5000]], nz
        print("OK")
    """)
    assert_no_crash(res)
    assert "OK" in res.stdout
