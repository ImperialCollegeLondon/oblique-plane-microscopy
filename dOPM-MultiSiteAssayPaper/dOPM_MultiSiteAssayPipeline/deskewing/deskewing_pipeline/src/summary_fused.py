import os
import shutil

"""Create a simple summary for fused TIFF stacks by copying representative files.
Usage: python summary_fused.py <fused-folder> --output SUMMARY
"""

def collect_representative(input_dir, out_dir, max_samples=10):
    os.makedirs(out_dir, exist_ok=True)
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.tif', '.tiff'))]
    files = sorted(files)
    if not files:
        print('No TIFF files found in', input_dir)
        return
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
    p.add_argument('input', help='Folder with fused TIFFs')
    p.add_argument('--output', default='summary_fused', help='Summary output folder')
    args = p.parse_args()

    collect_representative(args.input, args.output)
