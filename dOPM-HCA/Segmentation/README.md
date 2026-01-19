# Single-GPU Cellpose 3D segmentation (edit-and-run)

Single-GPU script to run Cellpose 3D segmentation across
all timepoints for one `(well, tile)`.


---

## Expected input files

The script expects one 3D TIFF per timepoint per channel with names like:

WellB2_tile0_fused_tp_12_ch_2.tif

Required parts:
- Well<well_id> : e.g. B2, C10
- tile<tile_index> : integer
- fused_tp_<tp> : integer timepoint
- ch_<ch> : integer channel
- .tif

Each channel is stored as a separate TIFF file.

---

## Output files

For each timepoint it writes a label mask:

cellpose_masks_Well<well>_tile<tile>_tp_<tp>.tif

These masks are saved as uint16 TIFFs.

If output exists and `SKIP_EXISTING_OUTPUTS=True`, the timepoint is skipped.

---

## Dependencies

Python 3.9+ recommended.

Install packages:

pip install numpy tifffile cellpose

Notes:
- Cellpose uses PyTorch under the hood. If you have CUDA-capable GPUs and correct drivers,
  Cellpose should run on GPU when `CellposeModel(gpu=True)` is used.
- You may need to install a CUDA-enabled PyTorch build depending on your environment.

---

## How to run

1) Edit `segment_cellpose_single_gpu.py` and set:
- INPUT_DIR
- OUTPUT_DIR
- WELL
- TILE
- CHANNELS_TO_SUM
- Cellpose parameters (DIAMETER, FLOW_THRESHOLD, CELLPROB_THRESHOLD)

2) Run:

python segment_cellpose_single_gpu.py

---


### Sum different channels
Edit:
CHANNELS_TO_SUM = [0, 1]

### Turn off zero replacement
Set:
REPLACE_ZEROS_WITH_MIN_NONZERO = False

### Overwrite outputs
Set:
SKIP_EXISTING_OUTPUTS = False

---

## Troubleshooting

- "No timepoints found":
  Check the input directory and that filenames match the expected pattern exactly.

- "Missing expected input file":
  One or more channels listed in CHANNELS_TO_SUM is not present for a timepoint.

- GPU not used:
  Make sure CUDA drivers are installed and that Cellpose/PyTorch can see the GPU.
  You can quickly test in Python:
    from cellpose.models import CellposeModel
    CellposeModel(gpu=True)
