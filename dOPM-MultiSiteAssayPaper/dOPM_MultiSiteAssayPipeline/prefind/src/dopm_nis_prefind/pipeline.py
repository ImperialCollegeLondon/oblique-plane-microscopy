from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any

from .config import load_config, setup_logging
from .nd2_utils import find_newest_nd2_recursively, get_nd2_metadata, read_nd2_z_stack, wait_until_file_stable
from .outputs import (
    display_original_and_filtered_output,
    extract_cropped_planes,
    generate_montage,
    save_montage,
    write_positions_to_file,
    write_positions_xml,
)
from .processing import filter_locations, segment_blobs_and_find_focus


def run_prefind_pipeline(config: dict[str, Any], nd2_file: str | Path | None = None) -> dict[str, Path | int]:
    """Run one stateless prefind pass using the original metadata and blob-finding methods."""
    directories = config["directories"]

    if nd2_file is None:
        nd2_file = find_newest_nd2_recursively(directories["nd2_files_directory"])
    nd2_file = Path(nd2_file)
    nd2_folder = nd2_file.parent
    basename = nd2_file.stem
    logging.info("Processing ND2 file: %s", nd2_file)

    stable_seconds = float(config.get("sync", {}).get("stable_file_seconds", 0))
    if stable_seconds > 0:
        wait_until_file_stable(nd2_file, stable_seconds=stable_seconds)

    z_stack = read_nd2_z_stack(nd2_file)
    if z_stack.ndim != 3:
        raise ValueError(f"ND2 file must contain a 3D z-stack, got shape {z_stack.shape}.")

    metadata = get_nd2_metadata(nd2_file)

    binary_mask, labeled_regions, blob_binary, blob_data = segment_blobs_and_find_focus(
        z_stack,
        metadata,
        config,
        allow_large=False,
    )
    logging.info("Total blobs found after size filtering: %d", len(blob_data))

    filtered = filter_locations(
        blob_data,
        config.get("filtering", {}).get("min_distance", 10),
        config.get("filtering", {}).get("n_largest", 10),
        max_z=blob_data[0]["z_planes"] if blob_data else z_stack.shape[0],
        voxel_sizes=metadata["voxel_sizes"],
        border_margin_um=config.get("filtering", {}).get("border_margin_um", 0),
        enforce_border=config.get("filtering", {}).get("enforce_border", True),
        image_shape=(metadata["sizes"]["X"], metadata["sizes"]["Y"]),
    )
    logging.info("Blobs retained after filtering: %d", len(filtered))

    output_folder = Path(directories.get("output_folder") or nd2_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    positions = [
        {
            "x": round(b["coordinates_phys"][0], 3),
            "y": round(b["coordinates_phys"][1], 3),
            "z": round(b["coordinates_phys"][2], 3),
        }
        for b in filtered
    ]

    points_txt = Path(directories["default_file_path"])
    points_xml = output_folder / f"{basename}_points.xml"
    montage_png = output_folder / f"{basename}_montage.png"
    summary_jpg = output_folder / f"{basename}_summary.jpg"

    write_positions_to_file(positions, points_txt)
    write_positions_xml(points_xml, filtered)

    montage_cfg = config.get("montages", {})
    crops = extract_cropped_planes(z_stack, filtered, montage_cfg.get("crop_size", [200, 200]))
    montage = generate_montage(
        crops,
        rows=montage_cfg.get("rows", 2),
        cols=montage_cfg.get("cols", 10),
        pad_val=montage_cfg.get("pad_value", 0),
    )
    save_montage(montage_png, montage)

    display_original_and_filtered_output(
        z_stack=z_stack,
        mip_all=binary_mask,
        mip_filtered=blob_binary,
        filtered_locations=filtered,
        file_name=basename,
        save_folder=str(output_folder),
        save_name=f"{basename}_summary",
        show_plots=montage_cfg.get("show_plots", False),
    )

    logging.info("Wrote %d positions", len(filtered))
    logging.info("Text positions: %s", points_txt)
    logging.info("XML positions:  %s", points_xml)
    logging.info("Montage:        %s", montage_png)
    logging.info("Summary:        %s", summary_jpg)

    return {
        "nd2_file": nd2_file,
        "n_candidates": len(blob_data),
        "n_selected": len(filtered),
        "points_txt": points_txt,
        "points_xml": points_xml,
        "montage_png": montage_png,
        "summary_jpg": summary_jpg,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one NIS-Elements dOPM prefind pass.")
    parser.add_argument("--config", default="configs/prefind_settings.yaml", help="Path to YAML config file")
    parser.add_argument("--nd2", default=None, help="Optional explicit ND2 file. If omitted, newest ND2 is used.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    config = load_config(args.config)
    setup_logging(config)
    run_prefind_pipeline(config, nd2_file=args.nd2)


if __name__ == "__main__":
    main()
