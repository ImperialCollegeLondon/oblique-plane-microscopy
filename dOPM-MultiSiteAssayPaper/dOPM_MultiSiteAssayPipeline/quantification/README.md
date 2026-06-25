# Quantification

This folder contains the MATLAB quantification scripts used for the paper snapshot.

The scripts operate on fused dOPM image volumes and generate per-field/per-spheroid CSV outputs. In broad terms, the workflow is:

1. load fused image volumes;
2. segment nuclei from the nuclear channel;
3. clean and separate touching nuclei using 3D morphological operations and watershed;
4. generate cytoplasmic collar regions around nuclei;
5. extract intensity, shape and spatial measurements;
6. write per-field CSV files;
7. combine per-field CSVs into site-level quantification tables.

These outputs are the basis for the processed CSVs in `../data/` and for the plotting/statistics scripts used in the paper.

## Main scripts

- `process_FOV.m` / `process_FOV_collar_modified.m`  
  Main per-field quantification routines.

- `three_scale_tophat.m`  
  Multi-scale top-hat style enhancement used during nuclear segmentation.

- `clean_and_watershed_nuclei.m` and `smooth_watershed.m`  
  Cleanup and 3D watershed separation of nuclear masks.

- `quantify_set_of_points.m`  
  Spatial/neighbourhood measurements for segmented objects.

- `generate_csv.m`  
  Combines per-field outputs into `main_quantification.csv` and `spatial_quantification.csv`.

- `launch.sh` and `dispatcher.slurm`  
  Example server/SLURM submission scripts used to run the MATLAB analysis on a compute cluster.

## External dependencies

This code relies partly on MATLAB helper functions and bioimage-analysis utilities from ALYtools:

<https://github.com/FLIMinator/ALYtools>

The original analysis was run in a server/HPC environment using Bash and SLURM wrappers. The paths in `launch.sh`, `dispatcher.slurm`, and some MATLAB files are local to the original analysis environment and should be edited before reuse.

## Important notes

This folder is included to document the analysis used for the paper. It is not intended to be a polished or maintained MATLAB package.

Expected reuse will require adapting:

- input/output paths;
- ALYtools location;
- MATLAB module/loading commands;
- cluster/SLURM settings;
- image naming conventions;
- channel ordering;
- voxel size and segmentation parameters, if used on new data.

For the scientific logic behind the segmentation, KTR readout and spheroid-level summaries, see the accompanying paper and the top-level repository README.