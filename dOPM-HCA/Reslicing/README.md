#  **README — dOPM Reslicing, Bead Registration, and BigStitcher Fusion Pipeline**

This repository implements a full data-processing workflow for **dual-view oblique plane microscopy (dOPM)** datasets.
It contains:

1. **Bead-based geometric registration**
2. **Deskewing and reslicing of biological sample volumes**
3. **Multi-view fusion in Fiji via BigStitcher**

The pipeline is designed for high-content multi-well timelapse imaging.

---

#  **Fiji Version**

All fusion and BDV metadata generation rely on a specific version of Fiji:

```
Fiji 2.9.0 (Linux 64-bit)
```

as referenced in:

```
configs/config.yaml  
fiji_executable_path: ".../fiji-2.9.0-linux64/Fiji.app/ImageJ-linux64"
```

---

#  **Required Acknowledgements**

### **npy2bdv — HDF5/BDV writer**

This repository includes a modified version of:

**npy2bdv – A Python tool to write NumPy arrays as BigDataViewer/BigStitcher HDF5**

Citation (required):
**Vladimirov N. npy2bdv. Zenodo (2022). DOI: 10.5281/zenodo.6148906**
[https://github.com/nvladimus/npy2bdv](https://github.com/nvladimus/npy2bdv)

### **BigStitcher / Multiview Reconstruction**

Fusion and view registration rely on Fiji’s BigStitcher plugin:

**GitHub:**
[https://github.com/JaneliaSciComp/BigStitcher](https://github.com/JaneliaSciComp/BigStitcher)
[https://github.com/JaneliaSciComp/multiview-reconstruction](https://github.com/JaneliaSciComp/multiview-reconstruction)

Citations (required):

* Hörl et al., *BigStitcher: reconstructing high-resolution image datasets of cleared and expanded samples.*, **Nat Methods (2019)**.
* Preibisch et al., *Software for bead-based registration of SPIM data.*, **Nat Methods (2010)**.
* Preibisch et al., *Efficient Bayesian-based Multiview Deconvolution.*, **Nat Methods (2014)**.

---

#  **dOPM Processing Workflow (High-Level)**

The pipeline performs **three major tasks**, each handled by dedicated scripts:

---

## ** Bead Registration (Calibration)**

**Scripts involved:**

* `scripts/register_beads_pipeline.py`
* `configs/beads_config.yaml`
* `src/dopm/data_converter.py`
* `src/dopm/metadata.py`
* `src/dopm/npy2bdv.py`

### **Purpose**

Estimate the geometric relationship between **View 1** and **View 2** using fluorescent bead datasets.

### **What happens**

1. Load bead volumes (usually one well or plate scan).
2. Deskew/reslice into BDV coordinate system.
3. Export to BDV/HDF5 using *npy2bdv*.
4. Call Fiji–BigStitcher headlessly via `fiji_bridge.py`.
5. BigStitcher performs bead-based registration.
6. Output:

   * `dataset.xml` with BigStitcher transforms
   * Affine matrices for each view
   * Metadata needed for biological datasets

### **Why**

Accurate dual-view geometry is essential for correct sample deskewing and fusion.

---

## ** Sample Deskewing & Reslicing (Biological Data)**

**Scripts involved:**

* `scripts/batch_process_plate.py`
* `scripts/run_pipeline.py`
* `src/dopm/data_converter.py` (deskew logic uses npy2bdv to generate hdf5 + xml dataset)
* `src/dopm/fusion.py` (uses BigStitcher expects xml dataset)
* `src/dopm/metadata.py`
* `configs/config.yaml`

### **Purpose**

Use bead-derived transforms to deskew the biological dataset into a **Cartesian, orthogonal** BDV volume.

### **What happens**

1. Load raw dOPM volumes (split by tile/well/timepoint).
2. Apply bead-inferred affine transforms.
3. Deskew using known mirror angle and pixel geometry.
4. Write each view to BDV format (`.h5 + .xml`) using `npy2bdv.py`.
5. Organize output in BDV folder structure for downstream Fiji fusion.

### **Why**

dOPM raw data are heavily sheared and tilted; proper deskewing is required for isotropic reconstructions.

---

## ** Fiji Fusion (BigStitcher)**

**Scripts involved:**

* `scripts/batch_fuse_plate.py`
* `src/dopm/fiji_bridge.py`
* `src/dopm/fusion.py`
* `configs/config.yaml`

### **Purpose**

Fuse View 1 and View 2 into a single high-quality volume using **Fiji’s BigStitcher** blending & deconvolution tools.

### **What happens**

1. Headless Fiji is launched with BigStitcher commands.
2. BDV XML files for all views/timepoints are loaded.
3. Pre-defined bead-based transformations are applied.
4. BigStitcher computes:

   * Intensity normalization
   * Overlap blending (linear/gaussian)
   * Optional multi-view deconvolution
5. Fused output is written back as BDV or OME-TIFF.

### **Why**

BigStitcher is optimized for multi-view OPM/SPIM fusion and is the gold-standard for this purpose.

---

#  **Source Modules Explained**

## `src/dopm/data_converter.py`

Handles:

* Loading raw OPM TIFF/ND2
* Deskew transformations
* Applying affine view transforms
* Preparing BDV arrays for export

Core of the geometry engine.

---

## `src/dopm/fiji_bridge.py`

Thin wrapper around calling Fiji headlessly:

* Launching the Fiji executable
* Passing BigStitcher commands
* Handling temp XMLs
* Logging output for batch mode

Used by bead registration and plate fusion.

---

## `src/dopm/fusion.py`

Implements:

* View ordering logic
* Creation of BigStitcher command strings
* Setup for blending & deconvolution
* Management of output directories

Does **not** do numerical fusion itself — BigStitcher does.

---

## `src/dopm/metadata.py`

Parses:

* Stage-scanning metadata
* Pixel sizes
* Mirror tilt
* Channel info
* Z-step geometry
  Produces structured metadata objects consumed by conversion scripts.

---

## `src/dopm/npy2bdv.py`

Integrated/modified copy of **npy2bdv**.

Used for:

* Writing BDV HDF5 files
* Writing BDV `.xml` descriptor
* Managing multi-scale pyramids (optional)

Citation required (see above).

---

#  **Scripts in Detail**

## `scripts/register_beads_pipeline.py`

Full pipeline for bead-based calibration:

1. Convert bead raw data
2. Write BDV volumes
3. Trigger BigStitcher registration
4. Export calibrated transforms

---

## `scripts/batch_process_plate.py`

Deskews **all wells/tiles** of the biological project using previously computed registration.

Key functionality:

* Plate-aware directory parsing
* Parallel processing of tiles
* Calls data_converter for each view/timepoint

---

## `scripts/batch_fuse_plate.py`

Runs BigStitcher fusion for an entire plate, well by well, tile by tile.

Supports:

* Workstation mode
* HPC per-tile mode (SLURM)
* Output fused volumes in BDV or TIFF

---

## `scripts/run_pipeline.py`

Entry point for a **complete end-to-end run**:

* Calls bead registration (optional)
* Deskews sample
* Runs fusion

Based on the `pipeline_settings.workflow` flag in config.yaml.

---

#  **SLURM Integration**

`slurm_example.sh` shows how to distribute per-well or per-tile jobs across an HPC cluster.

---

#  **Conclusion**

This repository implements a complete, modular, HPC-ready pipeline for:

1. **Bead-based dOPM geometric calibration**
2. **Deskewing and reslicing** into BigDataViewer format
3. **High-quality dual-view fusion** using Fiji BigStitcher

It correctly acknowledges and integrates:

* **npy2bdv** (DOI: 10.5281/zenodo.6148906)
* **BigStitcher / Multiview Reconstruction**
* **Fiji 2.9.0**


