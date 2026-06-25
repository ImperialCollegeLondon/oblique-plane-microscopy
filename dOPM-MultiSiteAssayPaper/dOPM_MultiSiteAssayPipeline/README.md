# dOPM Multi-Site Assay Pipeline

Archival code and processed data snapshot accompanying the paper:

**Multi-Site Reproducibility Study of 3D High-Content Analysis with Dual-View Oblique Plane Microscopy**

The data underlying the paper is freely available here:

<https://www.ebi.ac.uk/biostudies/submissions/edit/S-BIAD3591>

This repository records the acquisition, pre-finding, deskewing/fusion, quantification, plotting and statistical-analysis workflow used for the multi-site dOPM reproducibility study.

The repository is intended to help readers understand how the analysis was performed, inspect the processed data, and trace the scripts used to generate the paper figures and statistical outputs. 

## Study overview

The study used dual-view oblique plane microscopy (dOPM) to image 3D melanoma spheroids in 96-well plates across four sites. Spheroids expressed an ERK kinase translocation reporter (ERK-KTR), and the analysis quantified nuclear and cytoplasmic reporter localisation at the single-cell level.

The workflow captured here includes:

1. microscope acquisition protocol exports;
2. widefield pre-finding of spheroids for dOPM imaging;
3. dOPM deskewing, registration and fusion;
4. MATLAB-based 3D nuclear segmentation and KTR quantification;
5. processed CSV tables;
6. Python plotting scripts for paper figures;
7. R-based mixed-effects statistical analysis.

## Repository layout

```text
acquisition/
    NIS-Elements acquisition protocol exports for the imaging workflow.

prefind/
    Python code for widefield spheroid detection and position-list generation.

deskewing/
    Python/Fiji/BDV-related code for converting, registering, deskewing and fusing dOPM data.

quantification/
    MATLAB scripts for 3D nuclear segmentation, cytoplasmic collar generation and KTR quantification.
    Includes example Bash/SLURM scripts used to run analysis on a server/HPC environment.

data/
    Processed per-site quantification CSVs.
    Raw microscopy image data are not included.

plotting/
    Python scripts and generated CSV/figure outputs used for the paper plots.

statistics/
    R Markdown notebook and rendered output for the mixed-effects statistical analysis.
```

## Folder READMEs

Several folders contain additional notes describing their role in the snapshot:

- `prefind/README.md`
- `deskewing/README.md`
- `deskewing/deskewing_pipeline/README.md`
- `deskewing/src/dopm/README.md`
- `quantification/README.md`
- `data/README.md`
- `plotting/README.md`
- `statistics/README.md`

These are intended as lightweight guides rather than full user manuals.

## Processed data

The `data/` folder contains processed CSV outputs from the image-analysis pipeline, organised by site:

```text
data/Crick/
data/ICR/
data/IGC/
data/IRB/
```

Each site folder contains:

- `main_quantification.csv`
- `spatial_quantification.csv`

These files are downstream analysis outputs, not raw microscopy data. They are used by the plotting and statistics scripts to reproduce the paper-level summaries.

## Quantification

The `quantification/` folder contains MATLAB scripts used to segment nuclei, generate cytoplasmic collar regions and extract KTR intensity measurements from fused dOPM image volumes.

The quantification workflow was run on a server/HPC environment using Bash and SLURM wrapper scripts. Some paths and settings are specific to the original analysis environment and will need to be edited before reuse.

This part of the workflow relies partly on MATLAB helper functions and bioimage-analysis utilities from ALYtools:

<https://github.com/FLIMinator/ALYtools>

See `quantification/README.md` for a brief overview.

## Plotting

The `plotting/` folder contains Python scripts used to combine processed CSVs and generate the main paper-style plots.

The plotting scripts produce spheroid-level summaries from the per-cell quantification data, including:

- KTR sensor ratio per spheroid;
- number of segmented cells per spheroid;
- raw nuclear and KTR intensity summaries across sites.

Some plotting scripts contain hard-coded paths from the original analysis environment. These should be updated before rerunning.

See `plotting/README.md` for a brief overview.

## Statistics

The `statistics/` folder contains the R Markdown analysis used for the mixed-effects statistical analysis.

The statistical workflow follows the paper logic: per-cell measurements are aggregated to the spheroid level, then treatment and site effects are assessed using a mixed-effects model.

This analysis was contributed separately from the image-processing and plotting code, so the repository keeps this section as an analysis record rather than a maintained R package.

See `statistics/README.md` for a brief overview.

## Raw data availability

Raw dOPM microscopy datasets are not included in this repository. This repository contains code, protocol exports, processed quantification tables and generated analysis outputs.

## Reuse notes

This repository is provided for transparency and reproducibility of the paper analysis. It should be treated as an archival snapshot.

Before rerunning any part of the workflow, expect to update:

- local input/output paths;
- locations of Fiji/ImageJ, MATLAB and external tools;
- ALYtools path;
- Python/R/MATLAB environments;
- SLURM or cluster-specific settings;
- image naming conventions;
- channel ordering;
- voxel sizes and segmentation parameters, if applying the code to new data.

## Suggested reading order

For understanding the analysis logic, start with:

1. this top-level README;
2. `data/README.md`;
3. `plotting/README.md`;
4. `statistics/README.md`;
5. `quantification/README.md`;
6. the acquisition, prefind and deskewing folders if you need to trace the image-processing workflow upstream.

## Citation

If using this repository, please cite the associated paper:

**Multi-Site Reproducibility Study of 3D High-Content Analysis with Dual-View Oblique Plane Microscopy**


## Contributors

This repository contains contributions from:

* Hugh Sparks — repository assembly, acquisition, pre-finding, deskewing/fusion, plotting and overall analysis workflow
* Yuriy Alexandrov — MATLAB quantification workflow `quantification/`
* Kanad N. Mandke — R mixed-effects statistical analysis in `statistics/`

## License

This repository is released under the MIT License. See the `LICENSE` file for details.

Some components depend on or were adapted from third-party research software, including `npy2bdv` and ALYtools. Reuse of those components should also follow the terms of their original licences.




