# dOPM Shared ImageJ Scripts

Scripts for processing dual-view oblique plane microscopy (dOPM) datasets in Fiji/ImageJ using the Multiview Reconstruction framework / BigStitcher.

The scripts provide a lightweight Fiji interface for defining, geometrically transforming, registering, fusing, and exporting dOPM datasets. The implementation intentionally stays close to the BigStitcher plugin API so that datasets remain inspectable and editable through the Fiji GUI.

---

## Overview

This repository primarily supports dOPM datasets consisting of two obliquely acquired views, typically named as angle `0` and angle `70`. It also supports a no-registration single-view dataset creation path for data containing only one of those angles.

The scripts can:

- define BigStitcher multiview datasets from raw ND2 or TIFF stacks
- apply dOPM geometric transforms using XML metadata
- create and transform no-registration single-view datasets
- register views using bead datasets
- reuse an optimised bead registration for sample datasets
- define or copy bounding boxes
- export fused or single-view deskewed volumes
- generate maximum intensity projections (MIPs) for rapid quality control

The current design treats the BigStitcher dataset XML as the source of truth for spatial metadata and registration state.

---

## Installation

### Fiji

Use the tested Fiji distribution:

<https://imperialcollegelondon.app.box.com/s/2pc9iiusvuh36uc8arceoutrwxi193ul/file/1364388978888>

Other Fiji versions may work, but compatibility depends on the installed Multiview Reconstruction / BigStitcher and CLIJ versions.

### Script installation

Clone or copy this repository into:

```text
Fiji.app/plugins/Scripts/dOPM
```

After restarting Fiji, the scripts should appear under the `dOPM` menu.

---

## Dependencies

- Fiji / ImageJ
- Multiview Reconstruction / BigStitcher
- Bio-Formats
- CLIJ / CLIJ2, used for GPU-accelerated MIP generation
- Jython / ImageJ Python 2 scripting environment

The scripts are written for the Fiji Jython environment, so they avoid Python 3-only syntax.

---

## Data assumptions

### Acquisition

The current scripts assume a two-view dOPM acquisition with one file per timepoint, tile, and angle, for example:

```text
spim_Time0000_Tile0000_angle0.nd2
spim_Time0000_Tile0000_angle70.nd2
```

Optional well suffixes are supported:

```text
spim_Time0000_Tile0000_angle0__WellF5.nd2
spim_Time0000_Tile0000_angle70__WellF5.nd2
```

Both no-well and well-suffixed filenames are supported. Well-suffixed files are grouped into independent datasets such as:

```text
dataset_WellF5.xml
dataset_WellF6.xml
```

Files without a well suffix are processed as the default dataset:

```text
dataset.xml
```

### Single-view no-registration datasets

The `Transform one-view data` option in `make_mvr_dataset.py` is for data folders containing exactly one dOPM acquisition angle, normally either `angle0` or `angle70` for a 17.5 degree prism angle. The script detects the actual angle token from the filenames and creates a dataset containing only that angle.

Single-view mode deliberately does not run bead registration or copy bead registrations. It applies the corresponding geometric dOPM transform for the detected view and then leaves the XML ready for inspection/export. If the folder contains two angles, use the two-view options instead; if the two-view option is selected for a one-angle folder, the script now raises a clear error rather than creating an invalid two-angle dataset.

### File pattern

The intended canonical file pattern is:

```text
spim_Time{tttt}_Tile{xxxx}_angle{a}
```

The code parses the filename tokens `Time`, `Tile`, `angle`, and optional trailing `Well...` suffix. The file pattern is primarily passed to BigStitcher when defining the dataset.

---

## Main workflow

### 1. Make and register bead dataset

Use:

```text
dOPM → make_mvr_dataset.py
```

and choose the bead-registration workflow.

The bead dataset is first defined as a BigStitcher XML dataset, then dOPM geometry is applied, and then bead-based registration is run using BigStitcher interest points.

The bead registration should be visually checked in Fiji / BigStitcher. If needed, open the bead XML/HDF5 dataset, optimise or manually correct the registration, and save the updated XML.

The updated bead XML is the registration source for downstream sample processing.

### 2. Process sample data using bead registration

Sample datasets are defined and transformed in the same way as bead datasets, but the final view-registration step is copied from the bead XML.

The registration transfer is global:

- source registration is taken from bead timepoint `0`
- source registration is taken from bead tile `0`
- transforms are matched by channel and angle
- the transform set is applied to all sample timepoints, tiles, and wells

This reflects the assumption that one bead volume provides a global view-registration model for the whole experiment.

### 3. Define or copy bounding boxes

Use:

```text
dOPM → define_bounding_box.py
```

Available modes include:

- interactive/manual bounding box definition
- copy an existing bounding box from a reference XML
- automatic geometry-derived bounding box

Bounding boxes are stored in the dataset XML as `My Bounding Box` and can then be used during volume export/fusion.

### 4. Export deskewed or fused volumes

Use:

```text
dOPM → get_deskewed_dopm_volumes.py
```

This script reads the selected dataset XML and exports:

- fused volumes
- single-view volumes
- both single views
- selected subsets of timepoints and tiles
- batch outputs for multiple dataset XML files

### 5. Generate MIPs

Use:

```text
dOPM → get_fused_MIPs.py
```

This generates MIPs from exported TIFF stacks using CLIJ2. It can operate on a single output folder or search a root folder for dataset output folders matching a chosen volume type and binning.

---

## XML-first registration model


1. create and register the bead dataset
2. open the bead dataset in Fiji / BigStitcher
3. optimise or correct the registration
4. save the updated XML
5. use that updated XML for sample processing

---

## Output structure

Example output structure for a well-aware sample dataset:

```text
data/
  dataset_WellF5.xml
  dataset_WellF6.xml

output/
  dataset_WellF5/
    dataset_WellF5_fused_binning_2/
      *.tif
      MIP/
  dataset_WellF6/
    dataset_WellF6_fused_binning_2/
      *.tif
      MIP/
```

Exact output folder names depend on the selected export mode, volume type, and binning factor.

---

## Testing

### Test data

A small test dataset should be made available on Box.

Dummy Box link:

<https://imperialcollegelondon.box.com/s/2pc9iiusvuh36uc8arceoutrwxi193ul>

Expected local test layout:

```text
D:\temp\test_beads
├───data
│       spim_Time0000_Tile0000_angle0__WellF5.nd2
│       spim_Time0000_Tile0000_angle70__WellF5.nd2
│       spim_Time0000_Tile0001_angle0__WellF5.nd2
│       spim_Time0000_Tile0001_angle70__WellF5.nd2
│       spim_Time0000_Tile0002_angle0__WellF6.nd2
│       spim_Time0000_Tile0002_angle70__WellF6.nd2
│       spim_Time0001_Tile0000_angle0__WellF5.nd2
│       spim_Time0001_Tile0000_angle70__WellF5.nd2
│       spim_Time0001_Tile0001_angle0__WellF5.nd2
│       spim_Time0001_Tile0001_angle70__WellF5.nd2
│       spim_Time0001_Tile0002_angle0__WellF6.nd2
│       spim_Time0001_Tile0002_angle70__WellF6.nd2
│
├───fused_binning_2
├───v1
│       spim_Time0000_Tile0000_angle0.nd2
│       spim_Time0000_Tile0000_angle70.nd2
│
└───v2
        spim_Time0000_Tile0000_angle0__WellC2.nd2
        spim_Time0000_Tile0000_angle70__WellC2.nd2
```

This layout tests three important cases:

- bead data without a well suffix, in `v1`
- bead data with a well suffix, in `v2`
- sample data with multiple wells, tiles, timepoints, and angles, in `data`

### Basic test checklist

#### 1. Bead dataset without well suffix

Input:

```text
D:\temp\test_beads\v1
```

Expected:

```text
dataset.xml
```

The script should detect one bead group with no well suffix and create/register the bead dataset.

Check that:

- both angles are detected
- all channels are detected if present in the ND2
- calibration is applied without `dataset_calibrations.csv`
- registration runs
- the resulting dataset XML can be opened in BigStitcher

#### 2. Bead dataset with well suffix

Input:

```text
D:\temp\test_beads\v2
```

Expected:

```text
dataset_WellC2.xml
```

Check that the `__WellC2` suffix is detected and preserved as a separate well group.

#### 3. Sample data with multiple wells

Input:

```text
D:\temp\test_beads\data
```

Expected:

```text
dataset_WellF5.xml
dataset_WellF6.xml
```

Check that the sample data are split by well suffix.

For the supplied test tree:

- `WellF5` has two timepoints and two tiles
- `WellF6` has two timepoints and one tile
- both wells have two angles

#### 4. Single-view no-registration dataset

Create a test folder containing only one acquisition angle, for example:

```text
spim_Time0000_Tile0000_angle0.nd2
```

or:

```text
spim_Time0000_Tile0000_angle70.nd2
```

Run `make_mvr_dataset.py` and select `Transform one-view data`.

Check that:

- exactly one angle is detected
- the created dataset XML only contains that angle
- the geometric dOPM transform is applied
- no bead registration is run or copied
- choosing a two-view workflow on the same folder gives a clear validation error

#### 5. Global bead registration transfer

Use a bead XML from `v1` or `v2` as the bead registration source.

Check that:

- the source transform is read from bead timepoint `0`
- the source transform is read from bead tile `0`
- the transform is applied to all sample timepoints
- the transform is applied to all sample tiles
- the transform is applied to each matching channel and angle
- no `dataset_registrations.csv` is required

#### 6. Bounding box

Run:

```text
define_bounding_box.py
```

Test all relevant modes:

- define box interactively
- copy existing box from a bead/reference XML
- automatic geometry-based box

#### 7. Volume export

Run:

```text
get_deskewed_dopm_volumes.py
```

Check:

- fused export
- single-view export
- both single views
- subset export for selected timepoints and tiles
- batch export over all dataset XML files in a folder

Confirm that outputs are written to the expected dataset-specific folders.

#### 8. MIP generation

Run:

```text
get_fused_MIPs.py
```

Check:

- single-folder MIP generation
- search-root mode for dataset output folders
- MIP output folder creation
- TIFF outputs are readable in Fiji

---

## Development notes

### Running from shell or batch files

The current scripts are primarily designed as interactive Fiji scripts. This is intentional: bead registration and bounding-box definition benefit from manual quality control.

Possible future automation options include:

1. Add ImageJ script parameters using `#@` annotations.
2. Add a dedicated headless/batch runner script that reads a simple text, XML, JSON, or YAML configuration file.
3. Convert selected workflows into a fuller Fiji plugin.

For now, the interactive workflow is preferred because it keeps the code simple and encourages visual inspection of registration quality.

### Jython constraints

The scripts run in Fiji's ImageJ Python environment, which is based on Jython / Python 2. Avoid:

- f-strings
- pathlib
- Python 3-only syntax
- modern type annotations

---

## Design principles

- Keep the scripts readable and easy to modify.
- Use BigStitcher XML metadata as the source of truth.
- Avoid reslicing unless explicitly exporting volumes.
- Preserve interactive QC for bead registration and bounding boxes.
- Support well-aware datasets without requiring separate folders per well.

---

## References

- BigStitcher / Multiview Reconstruction:  
  <https://imagej.net/plugins/bigstitcher>

- Multiview Reconstruction:  
  <https://imagej.net/plugins/multiview-reconstruction>

- CLIJ:  
  <https://imagej.net/plugins/clij>

### Single-view no-registration folders with both angles present

`Transform one-view data` can now process one selected angle from a folder that still contains both dOPM views. Use the new **Single-view angle to use** field:

- leave it blank when the folder truly contains only one angle;
- enter `0` to process only `angle0`;
- enter `70` to process only `angle70` when using a 17.5 degree prism angle.

When a target angle is entered, the script filters the input file list before dataset creation, so BigStitcher only sees that one angle. The output dataset name includes the selected angle, for example `dataset_WellF5_angle70.xml`, to avoid overwriting a two-view or opposite-view XML from the same folder.

## License

This repository is released under the MIT License. See the `LICENSE` file for details.