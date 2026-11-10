#!/usr/bin/env python3
"""Cut a small, commit-friendly slice of real events for the equivalence tests.

Source: the h36m recording ``cam2_S11_Directions/h5/data.h5`` (not in the repo).
Its ``events`` dataset has shape (n, 4), dtype uint32, columns ``[t, x, y, p]``:
``t`` monotonic timestamp (us), ``x`` column, ``y`` row, ``p`` polarity in {0, 1}.
(Note: the polarity bit in the h5 file is the inverse of the one in the yarp
``ch0dvs/data.log`` AE packets; SCARF stores ``p`` but its surface does not
depend on it, and both implementations are fed the same values anyway.)

The sensor resolution is derived from the full recording (max coordinate + 1)
and stored in the fixture alongside the events.

Usage (from the repo root):
    python tests/make_fixture.py [--h5 PATH] [--start 3000000] [--count 50000]
"""
import argparse
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_H5 = HERE.parent.parent / "datasets/h36m/cam2_S11_Directions/h5/data.h5"
DEFAULT_OUT = HERE / "data" / "h36m_cam2_S11_Directions_slice.npz"


def load_h5_events(path):
    """Return (events[t, x, y, p] as uint32 (n, 4), width, height) from a data.h5 file."""
    import h5py

    with h5py.File(path, "r") as f:
        ev = f["events"][:]
    if ev.ndim != 2 or ev.shape[1] != 4:
        raise ValueError(f"unexpected events shape {ev.shape}")
    t, x, y, p = ev.T
    if not np.all(np.diff(t.astype(np.int64)) >= 0):
        raise ValueError("column 0 is not a monotonic timestamp")
    if not set(np.unique(p).tolist()) <= {0, 1}:
        raise ValueError("column 3 is not a {0,1} polarity")
    width, height = int(x.max()) + 1, int(y.max()) + 1
    return ev, width, height


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h5", type=Path, default=DEFAULT_H5)
    ap.add_argument("--start", type=int, default=3_000_000, help="index of the first event of the slice")
    ap.add_argument("--count", type=int, default=50_000, help="number of events in the slice")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ev, width, height = load_h5_events(args.h5)
    sl = ev[args.start : args.start + args.count]
    if len(sl) != args.count:
        raise SystemExit(f"slice too short: {len(sl)} events")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.out,
        t=sl[:, 0].astype(np.uint32),
        x=sl[:, 1].astype(np.uint16),
        y=sl[:, 2].astype(np.uint16),
        p=sl[:, 3].astype(np.uint8),
        sensor_size=np.array([width, height], dtype=np.int32),  # (width, height)
        source=np.array(f"{args.h5.name} events[{args.start}:{args.start + args.count}]"),
    )
    print(f"sensor {width}x{height}; wrote {len(sl)} events to {args.out} ({args.out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
