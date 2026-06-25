from __future__ import annotations

import os
import time
from pathlib import Path

import nd2
import numpy as np
import pandas as pd


def find_newest_nd2_recursively(base_dir: str | Path) -> Path:
    """Return the newest ND2 file below ``base_dir`` by creation time."""
    base_dir = Path(base_dir)
    nd2_files = [Path(root) / f for root, _, files in os.walk(base_dir) for f in files if f.lower().endswith(".nd2")]
    if not nd2_files:
        raise FileNotFoundError(f"No .nd2 files found under {base_dir}")
    return max(nd2_files, key=lambda p: p.stat().st_ctime)


def wait_until_file_stable(path: str | Path, stable_seconds: float = 2.0, poll_seconds: float = 0.5) -> None:
    """Wait until a file size has stopped changing for ``stable_seconds``."""
    path = Path(path)
    last_size = -1
    stable_since = None

    while True:
        size = path.stat().st_size
        now = time.monotonic()
        if size == last_size:
            if stable_since is None:
                stable_since = now
            elif now - stable_since >= stable_seconds:
                return
        else:
            stable_since = None
            last_size = size
        time.sleep(poll_seconds)


def read_nd2_z_stack(nd2_file: str | Path) -> np.ndarray:
    """Read the ND2 stack exactly as in the original workflow."""
    return np.asarray(nd2.imread(str(nd2_file)))


def get_nd2_metadata(nd2_file_path: str | Path) -> dict:
    """Extract ND2 sizes, voxel calibration and event table using the original method."""
    with nd2.ND2File(str(nd2_file_path)) as ndfile:
        sizes = dict(ndfile.sizes)
        sizes.setdefault("C", 1)
        sizes.setdefault("T", 1)
        sizes.setdefault("Z", 1)
        voxel_sizes = getattr(getattr(ndfile.frame_metadata(0).channels[0], "volume"), "axesCalibration")
        events = pd.DataFrame(ndfile.events())
    return {"sizes": sizes, "voxel_sizes": voxel_sizes, "events": events}
