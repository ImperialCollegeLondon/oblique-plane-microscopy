import os
import shutil

"""Create a simple summary of raw projections by copying a representative
projection per input folder into a `summary` folder for quick inspection.

Usage: python summary_raw.py <projections-folder> --output SUMMARY
"""


def collect_representative(input_dir, out_dir, max_samples=10):
    os.makedirs(out_dir, exist_ok=True)
    files = [f for f in os.listdir(input_dir) if f.lower().endswith('.tif')]
    files = sorted(files)
    if not files:
        print('No TIFF projections found in', input_dir)
        return
    # pick up to max_samples evenly distributed
    step = max(1, len(files) // max_samples)
    chosen = files[::step][:max_samples]
    for f in chosen:
        src = os.path.join(input_dir, f)
        dst = os.path.join(out_dir, f)
        shutil.copy2(src, dst)
        print('Copied', src, '->', dst)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('input', help='Folder with projection TIFFs')
    p.add_argument('--output', default='summary_raw', help='Summary output folder')
    args = p.parse_args()

    collect_representative(args.input, args.output)
