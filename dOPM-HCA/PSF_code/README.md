
#  README — PSF Detection & Analysis (MATLAB)

This folder contains two MATLAB scripts for automated **point spread function (PSF)** detection and quantitative PSF analysis from fluorescence bead images. The workflow uses **Bio-Formats** (via *bf-tools*) to read microscopy image formats (TIFF, ND2, OME-TIFF, CZI, LIF, etc.).

See Pramutka Kumar for latest version - https://github.com/pramukta/bf-tools

---

# Contents

### **1. `PFS_detection.m` — PSF Candidate Detection**

This script processes raw multi-plane fluorescence images (typically bead volumes) and identifies candidate point sources for PSF extraction.

**What it does:**

* Reads raw image stacks via **Bio-Formats** (`bfread.m` / `bfinit.m`)
* Subtracts camera offset and applies optional normalization
* Detects bright, isolated bead-like objects using:

  * thresholding
  * local maxima detection
  * size/intensity filtering
* Rejects beads near edges or overlapping with neighbours
* Saves:

  * bead coordinates
  * cropped bead sub-volumes
  * metadata for later analysis

**Output:** a MATLAB `.mat` file containing bead locations and corresponding cropped volumes.

---

### **2. `PFS_analysis.m` — PSF Quantitative Analysis**

This script takes the detected bead volumes and performs quantitative PSF measurements.

**What it does:**

* Loads bead sub-volumes collected from `PFS_detection.m`
* Computes standard PSF metrics, including:

  * Full-Width at Half-Maximum (FWHM) in X, Y, Z
  * Axial/lateral symmetry
  * Peak intensity and background
  * Radial / axial intensity profiles
* Fits Gaussian or empirical models to bead stacks
* Aggregates statistics across beads
* Produces plots summarizing PSF performance
* Optionally exports numerical results to CSV / MAT

**Output:**

* Struct containing FWHM and other PSF metrics
* Figures illustrating PSF shape
* Summary statistics table

---

# 🧩 Dependency: **bf-tools** (Bio-Formats MATLAB wrappers)

This project uses **bf-tools** by Pramukta Kumar to load microscopy files.

Included directory:

```
PSF_code/bf-tools/
```

bf-tools provides:

* `bfinit.m` — initializes Java Bio-Formats
* `bfread.m` — reads images using loci_tools
* `bfinfo.m` — retrieves image metadata
* `bfstream.m` — stream reader for large files

It bundles:

```
ext/loci_tools.jar
```

Bio-Formats is maintained by the OME consortium.

---

# Licensing & Attribution

### **bf-tools License (BSD 2-Clause)**

The bf-tools package included here is:

**Copyright (c) 2011, Pramukta Kumar
Georgetown University**

Redistribution and use in source and binary forms are permitted under the BSD-style license included in:

```
PSF_code/bf-tools/LICENSE
```

If you use **bf-tools** in scientific work, please acknowledge:

> *“bf-tools (MATLAB Bio-Formats wrappers) by Pramukta Kumar (2011)”*

Bio-Formats (loci_tools.jar) is distributed under OME licensing.

---

# Recommended Workflow

1. **Run `PFS_detection.m`**

   * Detect bead positions
   * Export bead sub-volumes

2. **Run `PFS_analysis.m`**

   * Quantify PSF shape
   * Compute FWHM and summary statistics

This two-step workflow provides reliable 3D PSF measurements for microscopy systems such as light-sheet, confocal, or OPM.



