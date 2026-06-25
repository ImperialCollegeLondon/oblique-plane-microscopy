# NIS-Elements synchronisation

This repo is designed for use inside a Nikon NIS-Elements JOBS workflow.

## Default sync protocol

| Value in `sync.txt` | Writer | Meaning |
|---|---|---|
| `0` | Python | Idle / Python has finished writing positions |
| `1` | NIS-Elements | A new prefind ND2 stack is ready for Python |
| `E` | Python | Error state; check the Python console/log |

Typical NIS-Elements job logic:

1. Acquire the 20x air wide-field prefind stack and save it as ND2.
2. Write `1` to `sync.txt`.
3. The Python watcher sees `1` and launches a fresh one-shot prefind subprocess.
4. Wait until `sync.txt` contains `0`.
5. Load the Python-generated positions, either from `points.txt` or the generated Nikon multipoint XML.
6. Continue to 60x water dOPM imaging.

## Watcher/subprocess design

The long-running watcher and the one-shot image-processing pipeline are deliberately separated. The watcher stays alive for the duration of the NIS-Elements JOBS experiment. Each time NIS-Elements writes the trigger value, normally `1`, the watcher starts a new child Python process equivalent to:

```powershell
python -m dopm_nis_prefind.pipeline --config configs/prefind_settings.yaml
```

If that child process finishes successfully, the watcher writes the configured complete value, normally `0`. If it fails, the watcher writes the configured error value, normally `E`, but the watcher itself remains alive.

## Original method boundary

The watcher and packaging are new infrastructure. The actual prefind method is intentionally the original method: 3D ND2 input, 2D MIP segmentation, uniform-filter background subtraction, Otsu thresholding with a 100 DN floor, 2D area filtering, mean-profile z-focus estimation, and original NIS metadata/stage-coordinate conversion.

## Why tracking was removed

Tracking was useful for timelapse prefind experiments, but it introduces stateful per-well CSV files and time indices. This repo is stateless: every trigger processes the newest ND2 stack independently and exports positions.

## Customising the sync values

The values are configurable in `configs/prefind_settings.yaml`:

```yaml
sync:
  file_path: "D:/test_outproc/sync.txt"
  trigger_value: "1"
  complete_value: "0"
  error_value: "E"
```

If your existing NIS job expects Python to write `2` on completion, set `complete_value: "2"`.
