#!/usr/bin/env python3
"""
HPC-ready batch_fuse_plate.py
Supports both workstation and per-tile cluster runs.

Usage examples:
  # Workstation (single well)
  python -m scripts.batch_fuse_plate --config configs/config.yaml --well B6

  # HPC mode (per tile)
  python -m scripts.batch_fuse_plate --config configs/config.yaml \
      --xml /path/to/dataset_WellB6_registered.xml --well B6 --tile 3

  # HPC resume mode (per tile and timepoint range)
  python -m scripts.batch_fuse_plate --config configs/config.yaml \
      --xml /path/to/dataset_WellB6_registered.xml --well B6 --tile 3 --tp-start 80 --tp-end 115
"""

import argparse
import os
import sys
import yaml
from src.dopm.fusion import FusionProcessor


def main():
    parser = argparse.ArgumentParser(
        description="Run fusion on registered datasets (per well or per tile)."
    )
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    parser.add_argument("--well", required=True, help="Well ID (e.g. B6)")
    parser.add_argument("--tile", type=int, help="Tile index (optional, for HPC mode)")
    parser.add_argument("--xml", help="Explicit XML path (for HPC mode)")
    parser.add_argument("--output-prefix", help="Optional prefix for fused output", default=None)
    parser.add_argument("--tp-start", type=int, help="Starting timepoint (optional, for resume)")
    parser.add_argument("--tp-end", type=int, help="Ending timepoint (optional, for resume)")

    args = parser.parse_args()

    # --- Load config ---
    with open(args.config, "r") as f:
        config = yaml.safe_load(f)

    output_path = config["data"]["output_path"]
    fiji_path = config["fiji_executable_path"]
    fusion_settings = config["fusion_settings"]

    # --- Determine XML path ---
    if args.xml:
        input_xml = args.xml
    else:
        input_xml = os.path.join(output_path, f"dataset_Well{args.well}_registered.xml")

    if not os.path.exists(input_xml):
        sys.exit(f" Error: Input XML not found at {input_xml}")

    # --- Clean up well name ---
    well_id = os.path.basename(args.well)
    well_id = well_id.replace("dataset_Well", "").replace("_registered.xml", "").replace(".xml", "").strip()

    if not well_id.startswith("Well"):
        well_id = f"Well{well_id}"

    # --- Always include tile ID (0 if not provided) ---
    tile_id = int(args.tile) if args.tile is not None else 0

    # --- Use clean prefix (no duplicate 'dataset_...' mess) ---
    output_prefix = args.output_prefix or well_id


    # --- Status summary ---
    print("\n--- Fusion Processing ---")
    print(f"Config file    : {args.config}")
    print(f"Well           : {args.well}")
    print(f"Input XML      : {input_xml}")
    print(f"Output prefix  : {output_prefix}")
    print(f"Using Fiji     : {fiji_path}")
    print(f"Tile index     : {tile_id}")
    if args.tp_start is not None and args.tp_end is not None:
        print(f"Timepoint range: {args.tp_start}-{args.tp_end}")
    else:
        print("Timepoints     : All")

    # --- Initialize FusionProcessor ---
    processor = FusionProcessor(fiji_path, fusion_settings)

    # --- Choose fusion mode ---
    if args.tp_start is not None and args.tp_end is not None:
        #  Resume/requeue mode — process a single tile and a specific TP range
        print(f"Running range-based fusion for tile {tile_id}, timepoints {args.tp_start}-{args.tp_end}")
        processor.fuse_single_tile_range(
            xml_path=input_xml,
            output_path=output_path,
            well_id=f"Well{args.well}",
            tile_id=tile_id,
            tp_start=args.tp_start,
            tp_end=args.tp_end,
        )

    elif args.tile is not None:
        #  HPC mode — one tile, all timepoints
        print(f"Running single-tile full fusion for tile {tile_id}")
        processor.fuse_volumes(
            input_xml,
            output_prefix=output_prefix,
            single_tile=args.tile
        )

    else:
        #  Workstation mode — all tiles, all timepoints
        print("Running full fusion for all tiles and timepoints")
        processor.fuse_volumes(
            input_xml,
            output_prefix=output_prefix
        )

    print(f"\n Fusion complete for Well {args.well}"
          + (f" (Tile {args.tile})" if args.tile is not None else "")
          + (f" [{args.tp_start}-{args.tp_end}]" if args.tp_start is not None else ""))


if __name__ == "__main__":
    main()
