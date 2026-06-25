import os
import numpy as np
import tifffile

"""Simple max Z-projection for TIFF stacks (fused data).
Usage: python fused_maxproj.py <input-file-or-folder> --output OUTPUT
"""


def list_tiff_files(input_path):
    if os.path.isfile(input_path):
        return [input_path] if input_path.lower().endswith(('.tif', '.tiff')) else []
    if not os.path.isdir(input_path):
        return []
    return sorted(os.path.join(input_path, f) for f in os.listdir(input_path) if f.lower().endswith(('.tif', '.tiff')))


def max_project_tiff(in_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    vol = tifffile.imread(in_path)
    # Ensure (Z,Y,X)
    if vol.ndim == 2:
        proj = vol
    else:
        proj = np.max(vol, axis=0)

    base = os.path.splitext(os.path.basename(in_path))[0]
    out_path = os.path.join(out_dir, f"max_{base}.tif")
    tifffile.imwrite(out_path, proj.astype(np.uint16))
    print(f"Saved max projection: {out_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Max Z-projection for fused TIFF stacks')
    parser.add_argument('input', help='TIFF file or folder')
    parser.add_argument('--output', default='fused_zprojections', help='Output folder')
    args = parser.parse_args()

    files = list_tiff_files(args.input)
    if not files:
        print('No TIFF files found at', args.input)
        exit(1)

    for f in files:
        max_project_tiff(f, args.output)
