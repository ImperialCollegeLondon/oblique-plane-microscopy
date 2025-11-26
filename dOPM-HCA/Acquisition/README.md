# **README — Nikon JOBS Workflow for Dual-View OPM High-Content Imaging**

This repository contains all JOBS scripts used in the **low-magnification overview → position refinement → high-resolution dual-view OPM** pipeline.
Below is a clear explanation of each script, what it does, and the recommended order in which to run them.

---

# 0 **Apply_dOPM_view_offsets_global_variables.html**

### **Purpose:**

Initializes *all* dOPM-specific global variables and view offsets used by every other script.

### **What it does:**

* Loads fixed calibration offsets between **View 1** and **View 2** (galvos, stage, piezo shifts)
* Defines the coordinate transforms required for dual-view imaging
* Creates global variables accessible to later JOBS scripts
* Ensures that View1 and View2 stacks are aligned spatially

### **Why it runs first:**

Every dOPM acquisition depends on these global offsets being correct.
This step establishes the geometry of the dual-view OPM.

---

# 1 **Get_Zmap_use_20x.html**

### **Purpose:**

Builds a **coarse Z-map** of the plate or region using a medium-magnification objective (10×–20×).

### **What it does:**

* Moves the stage through a coarse grid over the plate
* At each grid point, finds the **local best-focus Z**
* Saves a Z-map used for:

  * Autofocus correction
  * Adjusting positions from 4× overview → 20× → high-mag OPM
* Produces a smoothed height surface that compensates for plate tilt or sample curvature

### **Why it’s essential:**

dOPM has a <300um working distance — a good Z-map ensures the high-mag OPM does not touch bottom of sample.

---

# 2 **Scan_plate_overview.html**

### **Purpose:**

Acquire a **low-magnification (4×)** overview image of the entire sample or plate.

### **What it does:**

* Tiles the entire plate or region at 4×
* Captures brightfield / low-NA fluorescence
* Produces a stitched overview image
* Used to locate organoids, wells, or colonies
* Generates the first-pass **position list** of targets

### **Why it’s second:**

The overview is used to select targets that will later be imaged at higher magnification.

---

# 3 **Image_position_list.html**

### **Purpose:**

Revisit and image each overview-derived position at **intermediate magnification** (10×–20×).

### **What it does:**

* Loads the rough position list from the 4× overview
* Moves to each position using the Z-map
* Takes medium-resolution images
* Refines centroids / organoid boundaries
* Produces a cleaned-up position table for accurate high-mag targeting

### **Role in the pipeline:**

Acts as a refining step between rough 4× detection and fine OPM positioning.

---

# 4 **Adjust_position_list_manually.html**

### **Purpose:**

Provides a **human-in-the-loop** tool for manually reviewing and adjusting the refined position list.

### **What it does:**

* Loads the 20×-refined position list
* Displays each site individually
* Allows user to:

  * Delete positions
  * Add missing ones
  * Adjust X/Y/Z
* Saves the final “approved” high-accuracy position list

### **Why it exists:**

Automated detection is never perfect. This script ensures only valid targets proceed to OPM imaging.

---

# 5 **dOPM_acquisition_beads.html**

### **Purpose:**

Calibration acquisition using fluorescent beads, *not biological specimens*.

### **What it does:**

* Uses the same OPM acquisition pipeline as sample imaging
* But scans calibration beads instead
* Helps determine:

  * PSF shape
  * View1↔View2 alignment
  * Mirror angle offsets
  * Z-step consistency


### **Role:**

Ensures the dual-view fusion pipeline and deskew parameters are correct before imaging real biological samples.

---

# 6 **dOPM_acquistion.html**

### **Purpose:**

**The final high-resolution dual-view OPM acquisition script** for biological specimens.

### **What it does:**

* Loads the final manually-curated position list
* For each target:

  * Move to position (X/Y/Z)
  * Set View1 parameters
  * Acquire full Z-stack (hardware-triggered)
  * Switch to View2
  * Acquire matching Z-stack
  * Save volume per channel per view
* Supports:

  * Multi-channel imaging
  * Multi-well scanning
  * Time-lapse (if enabled)
* All geometry corrections rely on the previously applied global offsets

### **Output:**

Dual-view OPM datasets ready for deskewing, fusion, and reconstruction.

---

#  **Recommended Execution Order (Final Pipeline)**

```
0. Apply_dOPM_view_offsets_global_variables
1. Get_Zmap_use_20x
2. Scan_plate_overview (4×)
3. Image_position_list (20×)
4. Adjust_position_list_manually
5. dOPM_acquisition_beads   (optional but recommended)
6. dOPM_acquisition         (final high-mag dataset)
```

---

#  Summary Table

| Script                                       | Purpose                       | Stage of Pipeline  |
| -------------------------------------------- | ----------------------------- | ------------------ |
| **Apply_dOPM_view_offsets_global_variables** | Load OPM geometry + offsets   | **Initialization** |
| **Get_Zmap_use_20x**                         | Z-height map at 20×           | Pre-overview       |
| **Scan_plate_overview**                      | 4× tile scan                  | Overview           |
| **Image_position_list**                      | 20× revisit + refine          | Intermediate       |
| **Adjust_position_list_manually**            | Human refinement of positions | Pre-OPM            |
| **dOPM_acquisition_beads**                   | Calibration test run          | Optional           |
| **dOPM_acquistion**                          | Actual dual-view OPM imaging  | Final              |


