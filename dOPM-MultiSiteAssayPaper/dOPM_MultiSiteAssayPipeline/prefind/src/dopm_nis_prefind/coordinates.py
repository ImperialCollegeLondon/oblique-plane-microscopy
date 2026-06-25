from __future__ import annotations

import pandas as pd


def get_stage_coordinates(events_df: pd.DataFrame, z_index: int) -> dict[str, float]:
    """Return Nikon stage coordinates for a z-plane using the original NIS event columns."""
    row = events_df.iloc[z_index]
    return {
        "x": row["X Coord [µm]"],
        "y": row["Y Coord [µm]"],
        "z": row["Ti2 ZDrive [µm]"],
    }


def compute_physical_coordinates(region, z_index, voxel_sizes, stage_coords, stage_orientation, image_shape):
    """Convert a 2D region centroid to Nikon stage coordinates using the original method."""
    assert stage_orientation in ("flip", "normal"), f"Invalid stage orientation: {stage_orientation}"
    cy, cx = region.centroid[:2]
    vx, vy = voxel_sizes[:2]  # assumed to be in [Y, X] order from ND2, matching original code
    size_y, size_x = image_shape
    if stage_orientation == "flip":
        x = (-cx + size_x / 2) * vx + stage_coords["x"]
        y = (-cy + size_y / 2) * vy + stage_coords["y"]
    else:
        x = (cx - size_x / 2) * vx + stage_coords["x"]
        y = (cy - size_y / 2) * vy + stage_coords["y"]
    return x, y, stage_coords["z"]
