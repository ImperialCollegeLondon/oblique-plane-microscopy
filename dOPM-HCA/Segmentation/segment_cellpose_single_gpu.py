#!/usr/bin/env python3
"""
Single-GPU Cellpose 3D segmentation for one (well, tile) across all timepoints.
  - Designed for local use on one machine

Expected input filename pattern (one 3D volume per file):
  WellB2_tile0_fused_tp_12_ch_2.tif

Outputs:
  cellpose_masks_Well<well>_tile<tile>_tp_<tp>.tif
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import tifffile

from cellpose.models import CellposeModel


# -----------------------------------------------------------------------------
# USER SETTINGS (edit these)
# -----------------------------------------------------------------------------

INPUT_DIR = Path(r"/path/to/input_tiffs")
OUTPUT_DIR = Path(r"/path/to/output_masks")

# Choose a specific dataset subset to process
WELL = "B2"
TILE = 0

# Channels to load and sum into one volume (e.g. sum ch0 and ch1)
CHANNELS_TO_SUM = [0, 1]

# Cellpose parameters (tune as needed)
DIAMETER = 22.0
FLOW_THRESHOLD = 0.4
CELLPROB_THRESHOLD = 0.0

# Preprocessing: replace zeros with min nonzero value (helpful for padded volumes)
REPLACE_ZEROS_WITH_MIN_NONZERO = True

# If True, skip timepoints whose output mask already exists
SKIP_EXISTING_OUTPUTS = True


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def input_file_for(input_dir: Path, well: str, tile: int, tp: int, ch: int) -> Path:
    return input_dir / f"Well{well}_tile{tile}_fused_tp_{tp}_ch_{ch}.tif"


def discover_timepoints(input_dir: Path, well: str, tile: int, listing_channel: int) -> list[int]:
    """
    Discover all timepoints for a given (well, tile) by scanning filenames for one channel.
    """
    tp_re = re.compile(
        rf"^Well{re.escape(well)}_tile{tile}_fused_tp_(\d+)_ch_{listing_channel}\.tif$"
    )
    tps: list[int] = []
    for name in os.listdir(input_dir):
        m = tp_re.match(name)
        if m:
            tps.append(int(m.group(1)))
    return sorted(tps)


def load_and_sum_channels(
    input_dir: Path, well: str, tile: int, tp: int, channels: list[int]) -> np.ndarray:
    """
    Load and sum the requested channels into a float32 volume.

    Returns:
      vol: (Z, Y, X) float32
    """
    vol: np.ndarray | None = None
    for ch in channels:
        f = input_file_for(input_dir, well, tile, tp, ch)
        if not f.exists():
            raise FileNotFoundError(f"Missing expected input file: {f}")

        img = tifffile.imread(f).astype(np.float32)
        vol = img if vol is None else (vol + img)

    assert vol is not None
    return vol


def replace_zeros_with_min_nonzero(vol: np.ndarray) -> tuple[np.ndarray, int, float]:
    """
    Replace zeros with the minimum nonzero value (in-place).
    Returns (vol, n_zeros_replaced, min_nonzero_used).
    """
    nz = vol[vol > 0]
    if nz.size == 0:
        return vol, 0, 0.0

    min_nz = float(nz.min())
    mask = (vol == 0)
    n0 = int(mask.sum())
    if n0 > 0:
        vol[mask] = min_nz

    return vol, n0, min_nz


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    if not INPUT_DIR.exists():
        raise FileNotFoundError(f"INPUT_DIR does not exist: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    listing_channel = CHANNELS_TO_SUM[0]
    timepoints = discover_timepoints(INPUT_DIR, WELL, TILE, listing_channel)

    if not timepoints:
        raise RuntimeError(
            f"No timepoints found for Well{WELL} Tile{TILE} using channel {listing_channel}.\n"
            f"Check INPUT_DIR and filename pattern."
        )

    print(f"[INFO] Input:  {INPUT_DIR}")
    print(f"[INFO] Output: {OUTPUT_DIR}")
    print(f"[INFO] Target:  Well{WELL} Tile{TILE}")
    print(f"[INFO] Channels summed: {CHANNELS_TO_SUM}")
    print(f"[INFO] Found {len(timepoints)} timepoints: {timepoints[0]} .. {timepoints[-1]}")

    # Construct model once and reuse it.
    model = CellposeModel(gpu=True)

    n_ok = 0
    n_skip = 0
    n_err = 0

    for i, tp in enumerate(timepoints, start=1):
        out_path = OUTPUT_DIR / f"cellpose_masks_Well{WELL}_tile{TILE}_tp_{tp}.tif"

        if SKIP_EXISTING_OUTPUTS and out_path.exists():
            n_skip += 1
            print(f"[{i}/{len(timepoints)}] tp={tp} -> skip (exists)")
            continue

        try:
            vol = load_and_sum_channels(INPUT_DIR, WELL, TILE, tp, CHANNELS_TO_SUM)

            zeros_msg = ""
            if REPLACE_ZEROS_WITH_MIN_NONZERO:
                vol, n0, min_nz = replace_zeros_with_min_nonzero(vol)
                zeros_msg = f", zeros_replaced={n0}, min_nonzero={min_nz:.3f}"

            # Cellpose expects (Z, C, Y, X) when do_3D=True and channel_axis=1
            vol4 = vol[:, None, :, :]

            masks, *_ = model.eval(
                vol4,
                do_3D=True,
                z_axis=0,
                channel_axis=1,
                diameter=DIAMETER,
                flow_threshold=FLOW_THRESHOLD,
                cellprob_threshold=CELLPROB_THRESHOLD,
            )

            tifffile.imwrite(out_path, masks.astype(np.uint16))
            n_ok += 1
            print(f"[{i}/{len(timepoints)}] tp={tp} -> ok{zeros_msg}")

        except Exception as e:
            n_err += 1
            print(f"[{i}/{len(timepoints)}] tp={tp} -> error: {type(e).__name__}: {e}")

    print(
        f"[INFO] Done. ok={n_ok}, skipped={n_skip}, errors={n_err} "
        f"(Well{WELL} Tile{TILE})"
    )


if __name__ == "__main__":
    main()
