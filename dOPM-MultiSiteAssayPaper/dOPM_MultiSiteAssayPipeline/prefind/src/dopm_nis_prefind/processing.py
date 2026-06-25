from __future__ import annotations

from typing import Any

import numpy as np
from scipy.ndimage import label, uniform_filter
from skimage.filters import threshold_otsu
from skimage.measure import regionprops
from skimage.morphology import closing, disk
from skimage.segmentation import clear_border

from .coordinates import compute_physical_coordinates, get_stage_coordinates


def segment_blobs_and_find_focus(z_stack, metadata, config, allow_large=False):
    """Original 2D-MIP spheroid detection and focus-finding method.

    This is intentionally a direct refactor of the original implementation:
    maximum-intensity projection, broad uniform-filter background subtraction,
    Otsu thresholding with a floor of 100 DN, 2D connected components, area
    filtering, focus-plane estimation from the mean raw-intensity profile, and
    stage-coordinate conversion from NIS event metadata.
    """
    offset = config["image_processing"]["camera_offset"] * config["image_processing"]["binning"] ** 2
    z_stack = np.where(z_stack <= 0, offset, z_stack)
    voxel_sizes = metadata["voxel_sizes"]
    image_shape = (metadata["sizes"]["Y"], metadata["sizes"]["X"])

    mip = np.max(z_stack, axis=0).astype(np.float32)
    uniform_mip = uniform_filter(mip, size=config["image_processing"]["uniform_window_size"])
    dog_mip = mip - uniform_mip
    threshold = max(threshold_otsu(dog_mip), 100)
    binary_mip = clear_border(closing(dog_mip > threshold, disk(1)))
    labeled, _ = label(binary_mip)

    min_area = np.pi * (config["image_processing"]["min_radius"] / voxel_sizes[1]) ** 2

    if allow_large:
        max_radius = config["image_processing"].get("max_radius_tracking", config["image_processing"]["max_radius"])
    else:
        max_radius = config["image_processing"]["max_radius"]

    max_area = np.pi * (max_radius / voxel_sizes[1]) ** 2

    results = []
    filtered_binary = np.zeros_like(binary_mip, dtype=bool)

    for region in regionprops(labeled, intensity_image=dog_mip):
        if not (min_area <= region.area <= max_area):
            continue

        filtered_binary[labeled == region.label] = True

        coords_2d = region.coords
        profiles = np.array([z_stack[:, y, x] for y, x in coords_2d])
        mean_profile = profiles.mean(axis=0)
        z_focus = np.argmax(mean_profile)

        stage_coords = get_stage_coordinates(metadata["events"], z_focus)
        x, y, z = compute_physical_coordinates(
            region,
            z_focus,
            voxel_sizes,
            stage_coords,
            config["stage_orientation"],
            image_shape,
        )

        results.append(
            {
                "coordinates": (region.centroid[1], region.centroid[0], z_focus),
                "pixel_count": region.area,
                "coordinates_phys": (x, y, z),
                "mean_intensity_profile": mean_profile,
                "z_planes": z_stack.shape[0],
            }
        )

    return binary_mip, labeled, filtered_binary, results


def filter_locations(
    locations,
    min_distance,
    n_keep,
    max_z,
    voxel_sizes,
    border_margin_um=0,
    enforce_border=True,
    image_shape=None,
):
    """Original filtering method: remove edge z planes, optional border filter, keep largest separated blobs."""
    valid = [loc for loc in locations if loc["coordinates"][2] not in (0, max_z - 1)]

    if enforce_border and image_shape:
        margin_x = border_margin_um / voxel_sizes[0]
        margin_y = border_margin_um / voxel_sizes[1]
        width, height = image_shape
        valid = [
            loc
            for loc in valid
            if (
                margin_x <= loc["coordinates"][0] <= width - margin_x
                and margin_y <= loc["coordinates"][1] <= height - margin_y
            )
        ]

    selected = []
    for loc in sorted(valid, key=lambda x: x["pixel_count"], reverse=True):
        if all(
            np.linalg.norm(np.array(loc["coordinates_phys"]) - np.array(other["coordinates_phys"])) >= min_distance
            for other in selected
        ):
            selected.append(loc)
        if len(selected) >= n_keep:
            break

    return selected
