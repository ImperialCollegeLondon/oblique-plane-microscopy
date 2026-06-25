from __future__ import annotations

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import cv2 as cv
import matplotlib.pyplot as plt
import numpy as np


def write_positions_to_file(positions=None, file_path=None):
    """Write the original repeated x/y/z text format used by the NIS job."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if os.path.exists(file_path):
        os.remove(file_path)

    with open(file_path, "w") as f:
        if not positions:
            logging.warning("No positions to write. Creating a blank file.")
            return

        for pos in positions:
            if "x" in pos and "y" in pos and "z" in pos:
                f.write(f"x={pos['x']}\n")
                f.write(f"y={pos['y']}\n")
                f.write(f"z={pos['z']}\n")
            else:
                logging.error(f"Position {pos} missing one or more coordinates.")


def write_positions_xml(filepath, points):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("variant", version="1.0")
    no_name = ET.SubElement(root, "no_name", runtype="CLxListVariant")
    for i, pt in enumerate(points):
        point = ET.SubElement(no_name, f"Point{i:05d}", runtype="NDSetupMultipointListItem")
        for label, val in zip("XYZ", pt["coordinates_phys"]):
            ET.SubElement(point, f"d{label}Position", runtype="double", value=str(val))
        ET.SubElement(point, "bChecked", runtype="bool", value="true")
        ET.SubElement(point, "strName", runtype="CLxStringW", value=f"Point_{i:04d}")
        ET.SubElement(point, "dPFSOffset", runtype="double", value="-1.0")
        ET.SubElement(point, "baUserData", runtype="CLxByteArray", value="")
    ET.ElementTree(root).write(filepath, encoding="UTF-16", xml_declaration=True)


def extract_cropped_planes(z_stack, locations, crop_size):
    """Extract 2D crops from a 3D z-stack at each blob's z-plane."""
    crops = []
    dy, dx = crop_size
    for loc in locations:
        cx, cy, cz = map(int, loc["coordinates"])
        y0, y1 = max(0, cy - dy // 2), min(z_stack.shape[1], cy + dy // 2)
        x0, x1 = max(0, cx - dx // 2), min(z_stack.shape[2], cx + dx // 2)
        crop = z_stack[cz, y0:y1, x0:x1]
        crops.append(crop)
    return crops


def generate_montage(crops, rows, cols, pad_val=0):
    if not crops:
        return np.zeros((rows * 10, cols * 10), dtype=np.uint8)
    h = max(im.shape[0] for im in crops)
    w = max(im.shape[1] for im in crops)
    padded = [np.pad(im, ((0, h - im.shape[0]), (0, w - im.shape[1])), constant_values=pad_val) for im in crops]
    grid = np.full((rows * h, cols * w), pad_val, dtype=padded[0].dtype)
    for idx, img in enumerate(padded):
        r, c = divmod(idx, cols)
        if r < rows:
            grid[r * h : (r + 1) * h, c * w : (c + 1) * w] = img
    return grid


def display_original_and_filtered_output(
    z_stack,
    mip_all,
    mip_filtered,
    filtered_locations,
    file_name=None,
    save_folder=None,
    save_name=None,
    show_plots=False,
):
    """Original three-panel diagnostic output."""
    try:
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))

        mip_raw = np.max(z_stack, axis=0)
        axs[0].imshow(mip_raw, cmap="gray")
        axs[0].set_title(f"Raw Output - {file_name}")
        axs[0].axis("off")

        rejected = mip_all & ~mip_filtered

        rgb_filter = np.zeros((*mip_all.shape, 3), dtype=np.uint8)
        rgb_filter[..., 0] = rejected * 255
        rgb_filter[..., 2] = rejected * 255
        rgb_filter[mip_filtered] = [255, 255, 255]
        axs[1].imshow(rgb_filter)
        axs[1].set_title("Filtered: White = Pass, Magenta = Reject")
        axs[1].axis("off")

        base = mip_all.astype(np.uint8) * 255
        base_rgb = np.zeros((*base.shape, 3), dtype=np.uint8)
        base_rgb[..., 0][base > 0] = 255
        base_rgb[..., 2][base > 0] = 255

        for loc in filtered_locations:
            x, y, _ = map(int, loc["coordinates"])
            cv.circle(base_rgb, (x, y), 100, (0, 255, 0), -1)

        axs[2].imshow(base_rgb)
        axs[2].set_title("All blobs (magenta) + filtered (green)")
        axs[2].axis("off")

        if save_folder is not None and save_name is not None:
            save_path = os.path.join(save_folder, save_name + ".jpg")
            plt.savefig(save_path)

        plt.close(fig)

        if show_plots:
            plt.show()

    except Exception as e:
        logging.error(f"Error displaying montage: {str(e)}")
        if "fig" in locals():
            plt.close(fig)


def save_montage(filepath, montage):
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    plt.imsave(filepath, montage, cmap="gray")
