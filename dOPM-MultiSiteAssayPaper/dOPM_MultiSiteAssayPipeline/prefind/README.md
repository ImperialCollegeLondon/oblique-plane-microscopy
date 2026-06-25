# dOPM NIS-Elements prefind

A small Python repo for automatically pre-finding spheroids in Nikon NIS-Elements wide-field ND2 z-stacks and exporting positions for downstream dual-view oblique plane microscopy (dOPM) acquisition.

## Intended NIS-Elements workflow

1. NIS-Elements acquires a 20x air wide-field prefind z-stack and saves it as ND2.
2. NIS-Elements writes `1` to a shared `sync.txt` file.
3. The Python watcher detects the trigger and launches a fresh one-shot prefind subprocess.
4. The subprocess runs the original prefind algorithm and writes `points.txt`, a Nikon multipoint XML file, and diagnostic montages.
5. The watcher writes `0` to `sync.txt` when the subprocess completes successfully.
6. NIS-Elements continues with the 60x water dOPM acquisition at the generated positions.

The watcher/subprocess separation is intentional. If an individual prefind run fails, the sub process can die while the long-running watcher remains alive and writes the configured error value, normally `E`.

## Repository layout

```text
dOPM_NISPythonPrefind/
  README.md
  pyproject.toml
  requirements.txt
  configs/
    prefind_settings.yaml
  docs/
    nis_elements_sync.md
  scripts/
    run_prefind.py
    watch_sync_file.py
  src/dopm_nis_prefind/
    config.py
    coordinates.py
    nd2_utils.py
    outputs.py
    pipeline.py
    processing.py
    sync_watch.py
```

## Installation

From a Windows terminal in the repo folder:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Or, using an existing microscope-control environment:

```powershell
python -m pip install -e .
```

## Configure paths

Edit `configs/prefind_settings.yaml`:

```yaml
directories:
  nd2_files_directory: "D:/path/to/nis/prefind/nd2/folder"
  output_folder: "D:/test_outproc"
  default_file_path: "D:/test_outproc/points.txt"

sync:
  file_path: "D:/test_outproc/sync.txt"
  trigger_value: "1"
  complete_value: "0"
```

The prefind settings use the original parameter names:

```yaml
image_processing:
  camera_offset: 110
  binning: 4
  uniform_window_size: 1000
  min_radius: 10
  max_radius: 50

filtering:
  border_margin_um: 100
  min_distance: 100
  n_largest: 20
```

## Run one prefind manually

```powershell
dopm-prefind --config configs/prefind_settings.yaml
```

or with an explicit file:

```powershell
dopm-prefind --config configs/prefind_settings.yaml --nd2 "D:/path/to/prefind_stack.nd2"
```

## Run as a NIS-Elements sync watcher

Start this before running the NIS-Elements JOBS experiment:

```powershell
dopm-prefind-watch --config configs/prefind_settings.yaml
```

The watcher polls the sync file. When it sees `1`, it launches a fresh one-shot prefind subprocess using the same Python interpreter, processes the newest ND2 under `nd2_files_directory`, and then writes `0` to the sync file so the NIS-Elements job can continue.

If the child process exits with a non-zero error code, the watcher writes the configured error value, normally `E`, and continues watching for future triggers.

See `docs/nis_elements_sync.md` for the intended NIS job logic.

## Outputs

For each processed ND2 file, the pipeline writes:

- `points.txt`: simple repeated `x=`, `y=`, `z=` lines for legacy NIS JOBS parsing.
- `<nd2_basename>_points.xml`: Nikon Ti2/NIS multipoint XML list.
- `<nd2_basename>_montage.png`: crops of selected spheroids at their estimated focus planes.
- `<nd2_basename>_summary.jpg`: original three-panel diagnostic output.

## Original algorithm retained

The implementation intentionally follows the original code path:

1. Read the ND2 with `nd2.imread` and require a 3D `Z, Y, X` stack.
2. Extract metadata from `ndfile.sizes`, `frame_metadata(0).channels[0].volume.axesCalibration`, and `ndfile.events()`.
3. Use the original NIS event columns: `X Coord [µm]`, `Y Coord [µm]`, and `Ti2 ZDrive [µm]`.
4. Generate a 2D maximum-intensity projection over z.
5. Estimate broad background using `uniform_filter` on the MIP.
6. Compute `dog_mip = mip - uniform_mip`.
7. Threshold with `max(threshold_otsu(dog_mip), 100)`.
8. Apply `closing(..., disk(1))`, `clear_border`, and 2D connected-component labelling.
9. Filter 2D regions by area derived from `min_radius` and `max_radius`.
10. Estimate focus plane from the mean raw-intensity profile through z over each 2D region.
11. Convert centroids to Nikon stage coordinates using the original flip/normal stage-orientation transform.
12. Remove z-edge detections, optionally enforce XY border margin, and keep the largest physically separated positions.

## What was removed

The tracking/timelapse features were removed to keep this repo stateless:

- no per-well CSV databases
- no `time_index`
- no previous-blob matching
- no tracking-specific large-radius mode

Everything else in the prefind method should remain recognisable from the original scripts.
