
# Acquisition

This folder contains exported Nikon NIS-Elements JOBS definitions used to run the acquisition workflow for the multi-site dOPM reproducibility study.

Nikon JOBS is a visual programming environment for automated microscopy acquisition. In this repository, each acquisition step is stored as:

* `.bin` — the exported NIS-Elements JOBS definition, intended for re-import into NIS-Elements.
* `.html` — a human-readable export of the graphical JOBS workflow, included so the acquisition logic can be inspected without opening NIS-Elements.

These files document the acquisition workflow used for the paper. They are provided as an archival record rather than as a directly portable acquisition package. Hardware configuration, optical configurations, stage calibration, plate definitions, camera settings and device names may need to be adapted before reuse on another microscope.

## Files

```text
step_0_dOPM_offsets.bin
step_0_dOPM_offsets.html
```

Records the dOPM offset/setup job used before the main acquisition sequence.

```text
step_1_20x_zmap.bin
step_1_20x_zmap.html
```

Measures the plate surface/z-height map using the 20× air objective and Nikon Perfect Focus System. This z-map was used to define the starting z-position for later widefield pre-finding stacks.

```text
step_2_4x_widefield_overview.bin
step_2_4x_widefield_overview.html
```

Acquires a low-magnification brightfield overview image of each relevant well using the 4× objective. These overview images document spheroid distribution across the plate.

```text
step_3_20x_widefield_prefind.bin
step_3_20x_widefield_prefind.html
```

Acquires tiled 20× widefield epifluorescence z-stacks for spheroid pre-finding. These data were processed by the Python pre-finding code to identify suitable spheroids and generate position lists for high-resolution dOPM imaging.

```text
step_4_60xWI_dOPM_beads.bin
step_4_60xWI_dOPM_beads.html
```

Acquires 60× water-immersion dOPM bead volumes for dual-view registration and alignment checking. Bead imaging was performed around the sample acquisition to support view registration and assess optical stability.

```text
step_5_60xWI_dOPM_sample.bin
step_5_60xWI_dOPM_sample.html
```

Acquires the main 60× water-immersion dOPM sample data. The intended acquisition was two dOPM views per spheroid, three fluorescence channels and approximately 151 planes per view.

## Relationship to the paper workflow

The paper acquisition workflow consisted of:

1. plate z-map measurement with the 20× air objective;
2. 4× brightfield overview imaging;
3. 20× widefield epifluorescence pre-finding;
4. 60× water-immersion bead imaging for registration;
5. 60× water-immersion dOPM imaging of selected spheroids;
6. repeat bead imaging to check registration stability.

The exported JOBS files in this folder correspond to these acquisition stages and preserve the graphical NIS-Elements workflow definitions used in the study.

## Reuse notes

Before attempting to rerun these jobs, check and update:

* microscope hardware configuration;
* Nikon NIS-Elements version and JOBS module availability;
* objective names and optical configurations;
* camera names, exposure settings and binning settings;
* laser lines, filter sets and illumination settings;
* stage calibration and plate holder definition;
* well-plate definition;
* PFS/autofocus settings;
* output paths and ND2 saving locations;
* any site-specific dOPM offsets or device-control steps.

These jobs should therefore be treated as reproducibility documentation for the published workflow, not as guaranteed plug-and-play acquisition files.

See official Nikon documentation for further details on JOBS scripts
https://www.nisoftware.net/NikonSaleApplication/Help/Docs-AR/eng_ar/jobs.overview.html