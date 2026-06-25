# Processed data

This folder contains the processed quantification CSV files used in the paper snapshot.

The raw dOPM image data are not included in this repository. These CSV files are downstream outputs from the acquisition, prefind, deskewing/fusion and MATLAB quantification workflow.

## Folder layout

Each site folder contains two processed CSV files:

```text
Crick/
    main_quantification.csv
    spatial_quantification.csv

ICR/
    main_quantification.csv
    spatial_quantification.csv

IGC/
    main_quantification.csv
    spatial_quantification.csv

IRB/
    main_quantification.csv
    spatial_quantification.csv
```

The file `platemaps.txt` records the plate-map logic used to associate wells/rows with experimental conditions.

## File types

### `main_quantification.csv`

Per-cell/object quantification table.

Each row corresponds to one segmented object from a fused spheroid image volume. The table includes object-level measurements such as:

- site/well/tile information;
- nuclear segmentation properties;
- shape and volume measurements;
- nuclear and cytoplasmic/collar intensity statistics;
- cytoplasm-to-nucleus sensor ratio values.

### `spatial_quantification.csv`

Per-field/per-spheroid spatial summary table.

These files contain spatial and neighbourhood measurements derived from the detected object positions within each spheroid.

## How these data are used

The CSVs in this folder are combined by the plotting scripts in `../plotting/` to generate the paper figures and intermediate tables, including:

- `master_cross_partner.csv`;
- per-spheroid KTR ratio summaries;
- per-spheroid cell-count summaries;
- raw intensity summaries across sites.

The statistical analysis in `../statistics/` uses the combined table and performs inference at the spheroid level, rather than treating individual cells as independent biological replicates.

## Link to paper logic

These processed data correspond to the paper workflow in which 3D dOPM image volumes were segmented, per-cell KTR measurements were extracted, and the resulting per-cell measurements were aggregated to spheroid-level summaries for plotting and statistical analysis.

For the biological interpretation, treatment layout, site comparisons and mixed-effects modelling logic, see the accompanying paper.

## Important notes

These files are processed analysis outputs, not raw microscopy data.

They are included to make the paper analysis traceable and to allow readers to inspect or replot the quantified measurements without rerunning the full image-processing workflow.

