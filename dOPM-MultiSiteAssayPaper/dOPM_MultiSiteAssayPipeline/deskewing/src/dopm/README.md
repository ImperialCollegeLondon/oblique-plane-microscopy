# src/dopm

This folder contains the dOPM processing package components, including a modified copy of `npy2bdv.py`.

## Modified `npy2bdv.py`

This file is based on the `npy2bdv` template library, with the following custom adjustments:

- Added `BdvBase.read_affine_list(...)` to read the full list of affine transforms for a given view/timepoint.
- Added an informational `print("Creating group with name: {group_name}")` inside `BdvWriter.append_view(...)`.

These changes were retained because this version is the working version in the repository.

## Purpose

The `npy2bdv.py` class enables writing and editing BigDataViewer-compatible HDF5/XML datasets from NumPy arrays. It is used by the dOPM processing pipeline for generating and manipulating BDV/BigStitcher datasets.

## Notes

- The file is a customized, working version and should be treated as the authoritative local implementation.
- If the template is ever re-synced from the original `npy2bdv-master`, compare this version first to preserve the custom tweaks.
- The rest of `src/dopm` is the package used by the processing scripts in this repository.
