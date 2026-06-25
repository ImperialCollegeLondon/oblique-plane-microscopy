import os
import re
import numpy as np
import nd2
import tifffile

"""Minimal ND2 max Z-projection script.
Usage: python raw_maxproj.py <input-file-or-folder> --output OUTPUT [--pattern REGEX]
"""


def extract_max_projection_single_timepoint(nd2_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    data = nd2.imread(nd2_path, xarray=True)

    required = ['C', 'Z', 'Y', 'X']
    dims = list(data.dims)
    if not all(dim in dims for dim in required):
        raise ValueError(f"Missing one of required dimensions {required}, found {dims}")

    num_channels = data.sizes['C']
    base_name = os.path.splitext(os.path.basename(nd2_path))[0]

    for c_idx in range(num_channels):
        print(f"[Process] File={nd2_path}, C={c_idx}")
        vol = data.isel(C=c_idx)
        proj = vol.max(dim='Z')
        proj_np = np.asarray(proj).astype(np.uint16)

        out_name = f"max_{base_name}_ch{c_idx}.tif"
        out_path = os.path.join(output_dir, out_name)
        tifffile.imwrite(out_path, proj_np, dtype=np.uint16)
        print(f"Saved: {out_path} with shape {proj_np.shape}")


def list_nd2_files(input_path, pattern=None):
    if os.path.isdir(input_path):
        all_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith('.nd2')]
    else:
        all_files = [input_path]

    if pattern:
        regex = re.compile(pattern)
        all_files = [f for f in all_files if regex.search(os.path.basename(f))]

    return sorted(all_files)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Max Z-projection generator for ND2 time series.")
    parser.add_argument('input', help='ND2 file or folder')
    parser.add_argument('--output', default='zprojections', help='Output folder')
    parser.add_argument('--pattern', default=None, help='Optional regex pattern to filter ND2 files')
    args = parser.parse_args()

    nd2_files = list_nd2_files(args.input, args.pattern)
    if not nd2_files:
        print('No ND2 files found with given input/pattern.')
        exit(1)

    for nd2_file in nd2_files:
        print(f"\nProcessing: {nd2_file}")
        extract_max_projection_single_timepoint(nd2_file, args.output)
